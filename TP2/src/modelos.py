"""modelos.py - Modelos Pydantic y enumeración de estados.

Define la estructura de entrada/salida de la API y los estados posibles
de una tarea.  Pydantic valida los datos antes de que lleguen a la cola,
así una tarea inválida devuelve 422 sin encolarse (clase 19).
"""

from __future__ import annotations

import enum
import time
from typing import Any, Literal, Optional
from pydantic import BaseModel, Field, model_validator


# ---- Estados ---- #

class Estado(str, enum.Enum):
    """Estados posibles de una tarea en el sistema."""
    PENDIENTE = 'pendiente'
    EJECUTANDO = 'ejecutando'
    COMPLETADA = 'completada'
    FALLIDA = 'fallida'
    CANCELADA = 'cancelada'


# ---- Entrada ---- #

class TareaIn(BaseModel):
    """Payload del POST /tareas.

    Ejemplos válidos:
        {"tipo": "esperar",   "params": {"segundos": 5}}
        {"tipo": "descargar", "params": {"urls": ["https://example.com"]}}
        {"tipo": "hashear",   "params": {"texto": "hola", "iteraciones": 100000}}
    """
    tipo: Literal['esperar', 'descargar', 'hashear'] = Field(..., description='Tipo de tarea: esperar, descargar o hashear')
    params: dict[str, Any] = Field(default_factory=dict, description='Parámetros específicos del tipo')
    timeout: Optional[float] = Field(None, gt=0, description='Timeout en segundos (opcional, usa el default si no se envía)')

    @model_validator(mode='after')
    def _validar_params(self) -> 'TareaIn':
        """Valida params con el modelo de su tipo y los deja normalizados."""
        modelo = _PARAMS_POR_TIPO[self.tipo]
        self.params = modelo.model_validate(self.params).model_dump()
        return self


# ---- Params por tipo ---- #

class ParamsEsperar(BaseModel):
    segundos: float = Field(1, ge=0)


class ParamsDescargar(BaseModel):
    urls: list[str] = Field(..., min_length=1)


class ParamsHashear(BaseModel):
    texto: str = ''
    iteraciones: int = Field(1000, gt=0)


_PARAMS_POR_TIPO: dict[str, type[BaseModel]] = {
    'esperar': ParamsEsperar,
    'descargar': ParamsDescargar,
    'hashear': ParamsHashear,
}


# ---- Representación interna ---- #

class Tarea:
    """Representación interna de una tarea en el registro.

    No es un modelo Pydantic porque necesita guardar referencias a objetos
    no serializables (asyncio.Task).  La serialización a JSON para la API
    y para el volcado de estado se hace en métodos aparte.
    """

    __slots__ = (
        'id', 'tipo', 'params', 'estado', 'resultado', 'error',
        'creada_en', 'iniciada_en', 'terminada_en', 'timeout',
        'task_interno',
    )

    def __init__(self, id: str, tipo: str, params: dict[str, Any], timeout: float):
        self.id = id
        self.tipo = tipo
        self.params = params
        self.estado = Estado.PENDIENTE
        self.resultado: Any = None
        self.error: Optional[str] = None
        self.creada_en: float = time.time()
        self.iniciada_en: Optional[float] = None
        self.terminada_en: Optional[float] = None
        self.timeout = timeout
        self.task_interno = None  # asyncio.Task asignado por el worker

    def a_dict(self) -> dict[str, Any]:
        """Representación para la API (GET /tareas, GET /tareas/{id})."""
        d = {
            'id': self.id,
            'tipo': self.tipo,
            'params': self.params,
            'estado': self.estado.value,
            'creada_en': self.creada_en,
        }
        if self.iniciada_en is not None:
            d['iniciada_en'] = self.iniciada_en
        if self.terminada_en is not None:
            d['terminada_en'] = self.terminada_en
        if self.resultado is not None:
            d['resultado'] = self.resultado
        if self.error is not None:
            d['error'] = self.error
        return d

    def a_dict_volcado(self) -> dict[str, Any]:
        """Representación para el volcado JSON de estado (persistencia)."""
        return {
            'id': self.id,
            'tipo': self.tipo,
            'params': self.params,
            'estado': self.estado.value,
            'resultado': self.resultado,
            'error': self.error,
            'creada_en': self.creada_en,
            'iniciada_en': self.iniciada_en,
            'terminada_en': self.terminada_en,
            'timeout': self.timeout,
        }


# ---- Salida ---- #

class TareaOut(BaseModel):
    """Respuesta del POST /tareas (solo id y estado)."""
    id: str
    estado: str

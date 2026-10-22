"""api.py - Endpoints de la API REST (FastAPI).

Cinco rutas: POST, GET lista, GET detalle, DELETE y estadísticas.
El POST encola y responde inmediatamente (clase 19: endpoint async).
"""

from __future__ import annotations

import asyncio
import uuid
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from modelos import Estado, Tarea, TareaIn, TareaOut
from registro import Registro
from config import TIMEOUT_DEFAULT

logger = logging.getLogger(__name__)

router = APIRouter()

# Estas referencias se inyectan en main.py (lifespan)
_registro: Registro = None       # type: ignore[assignment]
_cola: asyncio.Queue = None      # type: ignore[assignment]
_pool = None                     # Pool (para ocupados)
_aceptando: bool = True


def configurar(registro: Registro, cola: asyncio.Queue, pool, aceptando_ref=None) -> None:
    """Inyecta las dependencias del módulo.

    Se llama una sola vez en el lifespan, antes de que lleguen requests.
    """
    global _registro, _cola, _pool
    _registro = registro
    _cola = cola
    _pool = pool


def dejar_de_aceptar() -> None:
    """Señala que no se aceptan tareas nuevas (apagado)."""
    global _aceptando
    _aceptando = False


# ---- POST /tareas ---- #

@router.post('/tareas', response_model=TareaOut, status_code=201)
async def crear_tarea(payload: TareaIn):
    """Encola una tarea y responde de inmediato con su id y estado.

    No hay ningún await del trabajo, así que la respuesta sale en
    milisegundos — no tarda lo que la tarea (clase 19).

    Devuelve 503 si no se aceptan tareas (apagado) o si la cola está
    llena (backpressure, clase 21).
    """
    if not _aceptando:
        raise HTTPException(status_code=503, detail='El servidor está apagándose')

    # tipo y params ya vienen validados por Pydantic (422 si son inválidos)

    # Crear tarea
    tarea_id = uuid.uuid4().hex[:12]
    timeout = payload.timeout if payload.timeout is not None else TIMEOUT_DEFAULT
    tarea = Tarea(id=tarea_id, tipo=payload.tipo, params=payload.params, timeout=timeout)

    # Registrar (sin await = atómico en el loop)
    _registro.registrar(tarea)

    # Encolar (put_nowait: si la cola está llena, salta QueueFull)
    try:
        _cola.put_nowait(tarea_id)
    except asyncio.QueueFull:
        # Sacamos la tarea del registro porque no se pudo encolar
        _registro.marcar_fallida(tarea_id, 'cola llena')
        raise HTTPException(status_code=503, detail='Cola de tareas llena')

    return TareaOut(id=tarea_id, estado=tarea.estado.value)


# ---- GET /tareas ---- #

@router.get('/tareas')
async def listar_tareas(estado: Optional[str] = Query(None, description='Filtrar por estado')):
    """Lista todas las tareas, con filtro opcional por estado.

    Ejemplo: GET /tareas?estado=pendiente
    """
    filtro = None
    if estado is not None:
        try:
            filtro = Estado(estado)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f'Estado no válido: {estado!r}. Usar: {[e.value for e in Estado]}',
            )

    return _registro.listar(filtro)


# ---- GET /tareas/{id} ---- #

@router.get('/tareas/{tarea_id}')
async def obtener_tarea(tarea_id: str):
    """Devuelve el estado y resultado de una tarea específica."""
    tarea = _registro.obtener(tarea_id)
    if tarea is None:
        raise HTTPException(status_code=404, detail=f'Tarea {tarea_id!r} no encontrada')
    return tarea.a_dict()


# ---- DELETE /tareas/{id} ---- #

@router.delete('/tareas/{tarea_id}')
async def cancelar_tarea(tarea_id: str):
    """Cancela una tarea encolada o en ejecución.

    - Si está PENDIENTE: la marca como CANCELADA; el worker la salteará.
    - Si está EJECUTANDO: cancela su asyncio.Task interno.
    - Si ya terminó (COMPLETADA/FALLIDA/CANCELADA): devuelve 409.
    """
    tarea = _registro.obtener(tarea_id)
    if tarea is None:
        raise HTTPException(status_code=404, detail=f'Tarea {tarea_id!r} no encontrada')

    if tarea.estado == Estado.PENDIENTE:
        _registro.marcar_cancelada(tarea_id)
        return {'id': tarea_id, 'estado': Estado.CANCELADA.value}

    if tarea.estado == Estado.EJECUTANDO:
        # Cancelamos el Task interno, no al worker
        if tarea.task_interno is not None and not tarea.task_interno.done():
            tarea.task_interno.cancel('cancelada por DELETE')
        return {'id': tarea_id, 'estado': 'cancelando'}

    # Ya terminó
    raise HTTPException(
        status_code=409,
        detail=f'La tarea ya está en estado {tarea.estado.value!r}',
    )


# ---- GET /estadisticas ---- #

@router.get('/estadisticas')
async def estadisticas():
    """Totales por estado, tiempos promedio y workers ocupados."""
    return _registro.estadisticas(_pool.ocupados)

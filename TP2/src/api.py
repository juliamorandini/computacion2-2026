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


def configurar(registro: Registro, cola: asyncio.Queue, pool) -> None:
    """Inyecta las dependencias del módulo.

    Se llama en cada arranque del lifespan, antes de que lleguen requests.
    Vuelve a aceptar tareas: si la app se apagó y se levanta de nuevo en el
    mismo proceso (pasa en los tests), _aceptando quedó en False.
    """
    global _registro, _cola, _pool, _aceptando
    _registro = registro
    _cola = cola
    _pool = pool
    _aceptando = True


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

    # Cola llena: se rechaza antes de registrar, así el registro no se llena
    # de tareas que el cliente nunca conoció (recibió 503, no un id).
    # Entre este chequeo y el put_nowait no hay ningún await: nadie puede
    # llenar la cola en el medio.
    if _cola.full():
        raise HTTPException(status_code=503, detail='Cola de tareas llena')

    # Crear tarea
    tarea_id = uuid.uuid4().hex[:12]
    timeout = payload.timeout if payload.timeout is not None else TIMEOUT_DEFAULT
    tarea = Tarea(id=tarea_id, tipo=payload.tipo, params=payload.params, timeout=timeout)

    # Registrar y encolar (sin await = atómico en el loop)
    _registro.registrar(tarea)
    _cola.put_nowait(tarea_id)

    return TareaOut(id=tarea_id, estado=tarea.estado.value)


# ---- GET /tareas ---- #

@router.get('/tareas')
async def listar_tareas(estado: Optional[Estado] = Query(None, description='Filtrar por estado')):
    """Lista todas las tareas, con filtro opcional por estado.

    Ejemplo: GET /tareas?estado=pendiente

    Al anotar el parámetro con el Enum, FastAPI valida el valor (422 si
    no es uno de los cinco estados) y /docs muestra las opciones.
    """
    return _registro.listar(estado)


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
        return TareaOut(id=tarea_id, estado=tarea.estado.value)

    if tarea.estado == Estado.EJECUTANDO:
        # Cancelamos el Task interno, no al worker.  cancel() solo pide la
        # cancelación: el CancelledError entra en el próximo await de la
        # tarea.  Esperamos a que termine de verdad (sin bloquear el loop:
        # es un await), así la respuesta trae el estado final y para
        # entonces las conexiones, el semáforo y el worker ya se liberaron.
        #
        # El worker hace await de este mismo Task desde antes, así que su
        # callback está primero en la lista: cuando el Task termina, el
        # worker marca 'cancelada' antes de que este await se despierte.
        task = tarea.task_interno
        if task is not None and not task.done():
            task.cancel('cancelada por DELETE')
            await asyncio.wait([task], timeout=1)
        return TareaOut(id=tarea_id, estado=tarea.estado.value)

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

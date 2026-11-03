#!/usr/bin/env python3
"""Clase 21 - Ejercicio 3, parte D: API con POST /hashear.

Dos modos, elegidos con la variable de entorno MODO:
    MODO=bloqueante  el calculo corre DENTRO del event loop (mal)
    MODO=executor    el calculo va a un ProcessPoolExecutor creado en el
                     lifespan (bien)

Uso (lo hace ej3_medir_api.py):
    MODO=executor uvicorn ej3_api_hashear:app --port 8001
"""
import asyncio
import hashlib
import os
from concurrent.futures import ProcessPoolExecutor
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

MODO = os.environ.get('MODO', 'executor')
VUELTAS = 3_000_000                    # ~5 s de CPU


def hashear(vueltas: int) -> str:
    """CPU-bound puro. Esta a nivel de modulo para poder viajar por pickle."""
    h = b'x'
    for _ in range(vueltas):
        h = hashlib.sha256(h).digest()
    return h.hex()[:8]


@asynccontextmanager
async def lifespan(app: FastAPI):
    # El pool se crea UNA vez al arrancar y se cierra al apagar.
    app.state.pool = ProcessPoolExecutor(max_workers=2)
    yield
    app.state.pool.shutdown(wait=True)


app = FastAPI(title='Tareas + hashear', lifespan=lifespan)

tareas: dict[int, dict] = {}
proximo_id = 0


class TareaNueva(BaseModel):
    tipo: Literal['descargar', 'hashear', 'esperar']
    prioridad: int = Field(default=1, ge=1, le=5)


@app.get('/tareas')
async def listar():
    return list(tareas.values())


@app.post('/tareas', status_code=201)
async def crear(nueva: TareaNueva):
    global proximo_id
    proximo_id += 1
    tareas[proximo_id] = {'id': proximo_id, **nueva.model_dump(),
                          'estado': 'pendiente'}
    return tareas[proximo_id]


@app.get('/tareas/{tarea_id}')
async def obtener(tarea_id: int):
    if tarea_id not in tareas:
        raise HTTPException(404, 'No existe esa tarea')
    return tareas[tarea_id]


@app.post('/hashear')
async def hashear_endpoint(vueltas: int = VUELTAS):
    if MODO == 'bloqueante':
        # SIN executor: el loop queda congelado todo el calculo.
        return {'modo': MODO, 'hash': hashear(vueltas)}

    loop = asyncio.get_running_loop()
    resultado = await loop.run_in_executor(app.state.pool, hashear, vueltas)
    return {'modo': MODO, 'hash': resultado}


"""comun.py - Utilidades compartidas por los scripts de medición.

URLs de la API y del servidor lento (por variable de entorno, así el mismo
script corre en el host o dentro del servicio 'mediciones' del compose),
percentiles y escritura de las tablas en mediciones/resultados/.
"""

from __future__ import annotations

import asyncio
import os
import statistics
import time
from pathlib import Path

import httpx

URL_API = os.getenv('URL_API', 'http://localhost:8000')
URL_LENTO = os.getenv('URL_LENTO', 'http://localhost:9000')
DIR_RESULTADOS = Path(__file__).parent / 'resultados'


# ---- Estadística ---- #

def percentil(valores: list[float], p: float) -> float:
    """Percentil p (0-100) por el método del rango más cercano."""
    ordenados = sorted(valores)
    k = max(0, min(len(ordenados) - 1, round(p / 100 * len(ordenados)) - 1))
    return ordenados[k]


def resumen_ms(valores: list[float]) -> dict[str, float]:
    """Mediana, p95 y máximo en milisegundos de una lista en segundos."""
    return {
        'mediana': statistics.median(valores) * 1000,
        'p95': percentil(valores, 95) * 1000,
        'max': max(valores) * 1000,
    }


# ---- API ---- #

async def esperar_api(cliente: httpx.AsyncClient, limite: float = 30) -> None:
    """Espera a que la API responda (después de un rearranque)."""
    fin = time.perf_counter() + limite
    while True:
        try:
            r = await cliente.get(f'{URL_API}/estadisticas')
            if r.status_code == 200:
                return
        except httpx.TransportError:
            pass
        if time.perf_counter() > fin:
            raise RuntimeError(f'La API en {URL_API} no respondió en {limite}s')
        await asyncio.sleep(0.5)


async def esperar_vacio(cliente: httpx.AsyncClient, intervalo: float = 0.1) -> None:
    """Espera hasta que no queden tareas pendientes ni ejecutando.

    Consulta /estadisticas y no GET /tareas porque la lista completa crece
    con cada tarea y serializarla también costaría tiempo de loop.
    """
    while True:
        r = await cliente.get(f'{URL_API}/estadisticas')
        totales = r.json()['totales']
        if totales['pendiente'] == 0 and totales['ejecutando'] == 0:
            return
        await asyncio.sleep(intervalo)


# ---- Resultados ---- #

def tabla_md(encabezados: list[str], filas: list[list]) -> str:
    """Arma una tabla markdown."""
    lineas = [
        '| ' + ' | '.join(encabezados) + ' |',
        '|' + '|'.join('---' for _ in encabezados) + '|',
    ]
    for fila in filas:
        lineas.append('| ' + ' | '.join(str(c) for c in fila) + ' |')
    return '\n'.join(lineas)


def guardar(nombre: str, contenido: str, modo: str = 'w') -> Path:
    """Escribe (o agrega) un archivo en mediciones/resultados/."""
    DIR_RESULTADOS.mkdir(exist_ok=True)
    ruta = DIR_RESULTADOS / nombre
    with open(ruta, modo, encoding='utf-8') as f:
        f.write(contenido + '\n')
    return ruta

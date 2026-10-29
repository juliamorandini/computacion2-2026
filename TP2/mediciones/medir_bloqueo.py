#!/usr/bin/env python3
"""medir_bloqueo.py - M2: latencia de GET /tareas durante un hash pesado.

Encola un 'hashear' de ~5 s y, mientras corre, pide GET /tareas cada 50 ms
y anota cuánto tarda cada respuesta.  Antes mide la latencia con la API
ociosa como referencia.

Hay que correrlo dos veces, rearrancando la API en cada modo:
  - HASH_EN_EXECUTOR=0: sha256 corre dentro de la corrutina y congela el loop.
  - HASH_EN_EXECUTOR=1: sha256 va al ProcessPoolExecutor (default).

Uso:
    HASH_EN_EXECUTOR=0 docker compose up -d api
    docker compose run --rm mediciones python medir_bloqueo.py --etiqueta "sin executor"
    HASH_EN_EXECUTOR=1 docker compose up -d api
    docker compose run --rm mediciones python medir_bloqueo.py --etiqueta "con executor"
"""

from __future__ import annotations

import argparse
import asyncio
import time

import httpx

from comun import URL_API, esperar_api, guardar, resumen_ms, tabla_md

INTERVALO = 0.05


async def medir_get(cliente: httpx.AsyncClient) -> tuple[float, list]:
    """Un GET /tareas: devuelve (latencia en s, lista de tareas)."""
    t0 = time.perf_counter()
    r = await cliente.get(f'{URL_API}/tareas')
    return time.perf_counter() - t0, r.json()


async def referencia(cliente: httpx.AsyncClient, n: int = 40) -> list[float]:
    """Latencias de GET /tareas con la API sin trabajo."""
    latencias = []
    for _ in range(n):
        lat, _ = await medir_get(cliente)
        latencias.append(lat)
        await asyncio.sleep(INTERVALO)
    return latencias


async def durante_hash(cliente: httpx.AsyncClient, iteraciones: int) -> tuple[list[float], dict]:
    """Encola el hash y lanza un GET /tareas cada 50 ms hasta verlo terminado.

    Cada GET sale a horario aunque el anterior no haya vuelto (create_task,
    no await): así, si el loop está congelado, se ve cuántos se acumulan y
    cuánto espera cada uno, en vez de una sola muestra larga.
    """
    r = await cliente.post(f'{URL_API}/tareas', json={
        'tipo': 'hashear',
        'params': {'texto': 'medicion', 'iteraciones': iteraciones},
        'timeout': 120,
    })
    r.raise_for_status()
    tarea_id = r.json()['id']

    enviados: list[asyncio.Task] = []
    while True:
        await asyncio.sleep(INTERVALO)
        enviados.append(asyncio.create_task(medir_get(cliente)))
        for t in enviados:
            if t.done():
                _, tareas = t.result()
                tarea = next(x for x in tareas if x['id'] == tarea_id)
                if tarea['estado'] not in ('pendiente', 'ejecutando'):
                    resultados = await asyncio.gather(*enviados)
                    return [lat for lat, _ in resultados], tarea


async def main(iteraciones: int, etiqueta: str) -> None:
    # Límite alto: con el loop congelado se acumulan ~100 GETs en vuelo
    limites = httpx.Limits(max_connections=500)
    async with httpx.AsyncClient(timeout=120, limits=limites) as cliente:
        await esperar_api(cliente)
        ociosa = await referencia(cliente)
        latencias, tarea = await durante_hash(cliente, iteraciones)

    duracion_hash = tarea['terminada_en'] - tarea['iniciada_en']
    r_ociosa = resumen_ms(ociosa)
    r_hash = resumen_ms(latencias)

    md = [
        f'## M2 — Event loop con hash pesado ({etiqueta})',
        '',
        f'`hashear` de {iteraciones:,} iteraciones: tardó {duracion_hash:.2f} s '
        f'(estado final: {tarea["estado"]}). GET /tareas cada {INTERVALO * 1000:.0f} ms.',
        '',
        tabla_md(
            ['Momento', 'GETs', 'Mediana (ms)', 'p95 (ms)', 'Máx (ms)'],
            [
                ['API ociosa', len(ociosa), f'{r_ociosa["mediana"]:.1f}', f'{r_ociosa["p95"]:.1f}', f'{r_ociosa["max"]:.1f}'],
                ['Durante el hash', len(latencias), f'{r_hash["mediana"]:.1f}', f'{r_hash["p95"]:.1f}', f'{r_hash["max"]:.1f}'],
            ],
        ),
        '',
    ]
    texto = '\n'.join(md)
    print(texto)
    ruta = guardar('m2_bloqueo.md', texto, modo='a')
    print(f'Agregado a {ruta}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--iteraciones', type=int, default=14_000_000)
    parser.add_argument('--etiqueta', required=True)
    args = parser.parse_args()
    asyncio.run(main(args.iteraciones, args.etiqueta))

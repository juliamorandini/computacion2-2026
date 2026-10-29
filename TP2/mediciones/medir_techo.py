#!/usr/bin/env python3
"""medir_techo.py - M3: techo del pool de workers.

Para cada N manda N POST /tareas a la vez (gather) y mide:
  - cuántas entraron (201) y cuántas rebotaron por cola llena (503),
  - latencia del POST (mediana y máxima),
  - tiempo total hasta que no queda nada pendiente ni ejecutando,
  - throughput (tareas aceptadas / tiempo total),
  - espera en cola de cada tarea (iniciada_en - creada_en).

La configuración del servidor (WORKERS, COLA_MAX, PROCESOS_CPU) se fija al
levantar la API; --etiqueta sirve para anotarla en la tabla.

Uso:
    WORKERS=4 COLA_MAX=100 docker compose up -d api
    docker compose run --rm mediciones python medir_techo.py \\
        --tipo esperar --segundos 1 --ns 1,10,100,500 --etiqueta "WORKERS=4 COLA_MAX=100"
"""

from __future__ import annotations

import argparse
import asyncio
import statistics
import time

import httpx

from comun import URL_API, esperar_api, esperar_vacio, guardar, tabla_md


def payload(tipo: str, segundos: float, iteraciones: int) -> dict:
    if tipo == 'esperar':
        return {'tipo': 'esperar', 'params': {'segundos': segundos}, 'timeout': 600}
    return {'tipo': 'hashear', 'params': {'texto': 'techo', 'iteraciones': iteraciones}, 'timeout': 600}


async def un_post(cliente: httpx.AsyncClient, cuerpo: dict) -> tuple[int, float, str | None]:
    """Un POST: devuelve (status, latencia en s, id si fue aceptada).

    Si la conexión falla (backlog del socket lleno, timeout) devuelve
    status 0: también es un dato del techo.
    """
    t0 = time.perf_counter()
    try:
        r = await cliente.post(f'{URL_API}/tareas', json=cuerpo)
    except httpx.TransportError:
        return 0, time.perf_counter() - t0, None
    lat = time.perf_counter() - t0
    return r.status_code, lat, r.json()['id'] if r.status_code == 201 else None


async def una_corrida(cliente: httpx.AsyncClient, n: int, cuerpo: dict) -> list:
    """Manda N POSTs juntos, espera a que se vacíe y arma la fila de la tabla."""
    t0 = time.perf_counter()
    posts = await asyncio.gather(*(un_post(cliente, cuerpo) for _ in range(n)))
    await esperar_vacio(cliente)
    total = time.perf_counter() - t0

    ids = {i for _, _, i in posts if i is not None}
    rechazadas = sum(1 for s, _, _ in posts if s == 503)
    errores = sum(1 for s, _, _ in posts if s == 0)
    lat_post = [lat for _, lat, _ in posts]

    tareas = (await cliente.get(f'{URL_API}/tareas')).json()
    espera_cola = [t['iniciada_en'] - t['creada_en'] for t in tareas
                   if t['id'] in ids and t.get('iniciada_en') is not None]

    fila = [
        n, len(ids), rechazadas, errores,
        f'{statistics.median(lat_post) * 1000:.0f}', f'{max(lat_post) * 1000:.0f}',
        f'{total:.2f}', f'{len(ids) / total:.1f}',
        f'{statistics.median(espera_cola):.2f}' if espera_cola else '-',
        f'{max(espera_cola):.2f}' if espera_cola else '-',
    ]
    print(' | '.join(str(c) for c in fila))
    return fila


async def main(tipo: str, ns: list[int], segundos: float, iteraciones: int, etiqueta: str) -> None:
    cuerpo = payload(tipo, segundos, iteraciones)
    # Sin tope práctico en el cliente: queremos que el cuello de botella
    # sea el servidor, no el pool de conexiones de httpx.
    limites = httpx.Limits(max_connections=max(ns))
    async with httpx.AsyncClient(timeout=600, limits=limites) as cliente:
        await esperar_api(cliente)
        filas = [await una_corrida(cliente, n, cuerpo) for n in ns]

    detalle = f'{segundos} s' if tipo == 'esperar' else f'{iteraciones:,} iteraciones'
    md = [
        f'## M3 — `{tipo}` de {detalle} ({etiqueta})',
        '',
        tabla_md(
            ['N', 'Aceptadas', '503', 'Error de conexión', 'POST mediana (ms)', 'POST máx (ms)',
             'Total (s)', 'Throughput (tareas/s)', 'Espera en cola mediana (s)', 'Espera en cola máx (s)'],
            filas,
        ),
        '',
    ]
    texto = '\n'.join(md)
    print(texto)
    ruta = guardar('m3_techo.md', texto, modo='a')
    print(f'Agregado a {ruta}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--tipo', choices=['esperar', 'hashear'], default='esperar')
    parser.add_argument('--ns', default='1,10,50,100,200,500,1000',
                        help='Cantidades de tareas separadas por coma')
    parser.add_argument('--segundos', type=float, default=1.0)
    parser.add_argument('--iteraciones', type=int, default=1_000_000)
    parser.add_argument('--etiqueta', required=True)
    args = parser.parse_args()
    ns = [int(x) for x in args.ns.split(',')]
    asyncio.run(main(args.tipo, ns, args.segundos, args.iteraciones, args.etiqueta))

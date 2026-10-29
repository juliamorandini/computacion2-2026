#!/usr/bin/env python3
"""medir_io.py - M1: 20 descargas secuenciales contra 20 concurrentes.

Parte 1 (cliente directo): descarga 20 URLs del servidor lento con un
'for' con await (secuencial) y con asyncio.gather (concurrente).  Cada URL
tiene una demora distinta (0.2 s a 1.15 s), así se ve que el secuencial
tarda la SUMA y el concurrente tarda lo que la MÁS LENTA.

Parte 2 (de punta a punta): manda las mismas 20 URLs como UNA tarea
'descargar' a la API y lee cuánto tardó la tarea según el propio registro
(terminada_en - iniciada_en).

Uso:
    docker compose run --rm mediciones python medir_io.py
    python medir_io.py --corridas 5          # desde el host, con httpx instalado
"""

from __future__ import annotations

import argparse
import asyncio
import statistics
import time

import httpx

from comun import URL_API, URL_LENTO, esperar_api, guardar, tabla_md

N_URLS = 20


def armar_urls() -> list[str]:
    """20 URLs con demoras de 0.20 s a 1.15 s (paso de 0.05 s)."""
    return [f'{URL_LENTO}/demora?s={0.2 + 0.05 * i:.2f}' for i in range(N_URLS)]


# ---- Parte 1: cliente directo ---- #

async def secuencial(cliente: httpx.AsyncClient, urls: list[str]) -> float:
    """Un await por vuelta: cada descarga empieza cuando termina la anterior."""
    t0 = time.perf_counter()
    for url in urls:
        r = await cliente.get(url)
        r.raise_for_status()
    return time.perf_counter() - t0


async def concurrente(cliente: httpx.AsyncClient, urls: list[str]) -> float:
    """gather lanza las 20 a la vez: las esperas de red se solapan."""
    t0 = time.perf_counter()
    respuestas = await asyncio.gather(*(cliente.get(u) for u in urls))
    for r in respuestas:
        r.raise_for_status()
    return time.perf_counter() - t0


# ---- Parte 2: a través de la API ---- #

async def por_api(cliente: httpx.AsyncClient, urls: list[str]) -> dict:
    """Encola una tarea 'descargar' con las 20 URLs y espera a que termine."""
    r = await cliente.post(f'{URL_API}/tareas', json={
        'tipo': 'descargar', 'params': {'urls': urls},
    })
    r.raise_for_status()
    tarea_id = r.json()['id']

    while True:
        tarea = (await cliente.get(f'{URL_API}/tareas/{tarea_id}')).json()
        if tarea['estado'] not in ('pendiente', 'ejecutando'):
            break
        await asyncio.sleep(0.05)

    if tarea['estado'] != 'completada':
        raise RuntimeError(f'La tarea terminó en {tarea["estado"]}: {tarea.get("error")}')
    descargas = tarea['resultado']['descargas']
    return {
        'total': tarea['terminada_en'] - tarea['iniciada_en'],
        'mas_lenta': max(d['segundos'] for d in descargas),
        'suma': sum(d['segundos'] for d in descargas),
    }


# ---- Main ---- #

async def main(corridas: int, etiqueta: str) -> None:
    urls = armar_urls()
    suma_teorica = sum(0.2 + 0.05 * i for i in range(N_URLS))
    mas_lenta_teorica = 0.2 + 0.05 * (N_URLS - 1)

    # Una conexión por URL, así el pool de httpx no serializa nada
    limites = httpx.Limits(max_connections=N_URLS)
    async with httpx.AsyncClient(timeout=30, limits=limites) as cliente:
        await esperar_api(cliente)

        # Una pasada de calentamiento (abre conexiones, DNS del compose)
        await concurrente(cliente, urls)

        t_seq, t_conc = [], []
        for i in range(corridas):
            t_seq.append(await secuencial(cliente, urls))
            t_conc.append(await concurrente(cliente, urls))
            print(f'corrida {i + 1}: secuencial {t_seq[-1]:.2f}s  concurrente {t_conc[-1]:.2f}s')

        api = await por_api(cliente, urls)

    med_seq = statistics.median(t_seq)
    med_conc = statistics.median(t_conc)

    md = [
        f'## M1 — Concurrencia I/O ({etiqueta})',
        '',
        f'20 URLs del servidor lento con demoras de 0.20 a 1.15 s '
        f'(suma teórica {suma_teorica:.2f} s, la más lenta {mas_lenta_teorica:.2f} s). '
        f'Mediana de {corridas} corridas.',
        '',
        tabla_md(
            ['Modo', 'Mediana (s)', 'Mín (s)', 'Máx (s)'],
            [
                ['Secuencial (`for` + `await`)', f'{med_seq:.2f}', f'{min(t_seq):.2f}', f'{max(t_seq):.2f}'],
                ['Concurrente (`asyncio.gather`)', f'{med_conc:.2f}', f'{min(t_conc):.2f}', f'{max(t_conc):.2f}'],
            ],
        ),
        '',
        f'**Speedup: {med_seq / med_conc:.1f}x**',
        '',
        'De punta a punta, una tarea `descargar` con las mismas 20 URLs:',
        '',
        tabla_md(
            ['Tiempo de la tarea (s)', 'Descarga más lenta (s)', 'Suma de las 20 (s)'],
            [[f'{api["total"]:.2f}', f'{api["mas_lenta"]:.2f}', f'{api["suma"]:.2f}']],
        ),
        '',
    ]
    texto = '\n'.join(md)
    print(texto)
    ruta = guardar('m1_io.md', texto, modo='a')
    print(f'Agregado a {ruta}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--corridas', type=int, default=3)
    parser.add_argument('--etiqueta', default='MAX_DESCARGAS_SIMULTANEAS=10')
    args = parser.parse_args()
    asyncio.run(main(args.corridas, args.etiqueta))

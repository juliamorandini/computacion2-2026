"""test_concurrencia_y_cpu.py - I/O concurrente, CPU fuera del loop y hash."""

import asyncio
import hashlib
import time

import tareas
from cpu import sha256_bloque
from utiles import crear, esperar_estado


# ---- descargar ---- #

async def test_descargas_de_una_tarea_son_concurrentes(cliente):
    """5 descargas de 0.3 s tardan lo que la más lenta, no la suma (1.5 s)."""
    urls = ['http://lento/demora?s=0.3'] * 5
    tid = await crear(cliente, 'descargar', {'urls': urls})

    t = await esperar_estado(cliente, tid, {'completada', 'fallida'})

    assert t['estado'] == 'completada'
    assert t['terminada_en'] - t['iniciada_en'] < 0.6


async def test_descargar_informa_status_bytes_y_tiempo_de_cada_url(cliente):
    tid = await crear(cliente, 'descargar', {'urls': ['http://lento/demora?s=0&bytes=200000']})

    t = await esperar_estado(cliente, tid, {'completada', 'fallida'})

    [d] = t['resultado']['descargas']
    assert d['status'] == 200
    assert d['bytes'] == 200_000
    assert d['segundos'] >= 0


async def test_descargar_con_una_url_caida_completa_con_el_error_de_esa_url(cliente):
    urls = ['http://caido/x', 'http://lento/demora?s=0']
    tid = await crear(cliente, 'descargar', {'urls': urls})

    t = await esperar_estado(cliente, tid, {'completada', 'fallida'})

    assert t['estado'] == 'completada'
    caida, sana = t['resultado']['descargas']
    assert 'ConnectError' in caida['error']
    assert sana['status'] == 200


async def test_descargar_con_todas_las_urls_caidas_termina_fallida(cliente):
    tid = await crear(cliente, 'descargar', {'urls': ['http://caido/a', 'http://caido/b']})

    t = await esperar_estado(cliente, tid, {'completada', 'fallida'})

    assert t['estado'] == 'fallida'
    assert 'fallaron las 2 descargas' in t['error']


# ---- hashear ---- #

def test_hash_en_bloques_da_lo_mismo_que_de_una_vez():
    """Partir el cálculo en bloques no cambia el resultado: cada bloque
    trabaja sobre los bytes crudos del anterior."""
    assert sha256_bloque(sha256_bloque(b'hola', 700), 300) == sha256_bloque(b'hola', 1000)


async def test_hashear_devuelve_el_sha256_iterado_correcto(cliente):
    # 250.000 iteraciones con bloques de 100.000: dos bloques llenos y uno parcial
    tid = await crear(cliente, 'hashear', {'texto': 'hola', 'iteraciones': 250_000})

    t = await esperar_estado(cliente, tid, {'completada', 'fallida'})

    esperado = b'hola'
    for _ in range(250_000):
        esperado = hashlib.sha256(esperado).digest()
    assert t['resultado']['hash'] == esperado.hex()


async def test_get_no_se_frena_durante_un_hash_pesado(cliente):
    """Con executor, el loop queda libre mientras otro proceso calcula."""
    tid = await crear(cliente, 'hashear', {'texto': 'x', 'iteraciones': 3_000_000})
    await esperar_estado(cliente, tid, {'ejecutando'})

    latencias = []
    while True:
        t0 = time.perf_counter()
        r = await cliente.get('/tareas')
        latencias.append(time.perf_counter() - t0)
        if r.json()[0]['estado'] != 'ejecutando':
            break
        await asyncio.sleep(0.02)

    assert len(latencias) > 5          # hubo GETs mientras calculaba
    assert max(latencias) < 0.05


async def test_sin_executor_el_hash_congela_el_loop(cliente, monkeypatch):
    """El contraejemplo de M2: el mismo hash dentro de la corrutina.

    Se mide como en la clase 21: un sleep de 50 ms que, con el loop
    ocupado en el hash, no se despierta hasta que el cálculo termina.
    """
    monkeypatch.setattr(tareas, 'HASH_EN_EXECUTOR', False)
    await crear(cliente, 'hashear', {'texto': 'x', 'iteraciones': 1_500_000})

    t0 = time.perf_counter()
    await asyncio.sleep(0.05)
    atraso = time.perf_counter() - t0 - 0.05

    assert atraso > 0.2

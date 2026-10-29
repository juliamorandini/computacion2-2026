"""test_backpressure_y_apagado.py - Cola llena, apagado ordenado y volcado."""

import asyncio
import json
import logging
import time

import api
from modelos import Estado, Tarea
from persistencia import reportar_volcado_previo
from pool import Pool
from registro import Registro
from utiles import crear, esperar_estado


# ---- Backpressure ---- #

async def test_cola_llena_devuelve_503_y_no_deja_tarea_fantasma(levantar):
    async with levantar(WORKERS=1, COLA_MAX=2) as c:
        corriendo = await crear(c, 'esperar', {'segundos': 5})
        await esperar_estado(c, corriendo, {'ejecutando'})     # salió de la cola
        await crear(c, 'esperar', {'segundos': 5})
        await crear(c, 'esperar', {'segundos': 5})             # cola llena

        r = await c.post('/tareas', json={'tipo': 'esperar', 'params': {}})

        assert r.status_code == 503
        assert len((await c.get('/tareas')).json()) == 3


async def test_durante_el_apagado_el_post_devuelve_503(cliente):
    api.dejar_de_aceptar()

    r = await cliente.post('/tareas', json={'tipo': 'esperar', 'params': {}})

    assert r.status_code == 503


async def test_despues_de_reiniciar_la_app_vuelve_a_aceptar_tareas(levantar):
    async with levantar() as c:
        await crear(c, 'esperar', {'segundos': 0})
    # El apagado puso _aceptando en False; el arranque siguiente lo tiene
    # que volver a True.
    async with levantar() as c:
        r = await c.post('/tareas', json={'tipo': 'esperar', 'params': {}})
        assert r.status_code == 201


# ---- Apagado ordenado ---- #

async def test_apagado_drena_cancela_lo_que_no_llega_y_vuelca_estado(levantar, tmp_path):
    async with levantar(WORKERS=2, LIMITE_APAGADO=0.5) as c:
        corta = await crear(c, 'esperar', {'segundos': 0.2})
        larga = await crear(c, 'esperar', {'segundos': 30})
        await esperar_estado(c, larga, {'ejecutando'})
        en_cola = await crear(c, 'esperar', {'segundos': 1})
    # Al salir del bloque corrió el shutdown del lifespan

    [archivo] = tmp_path.glob('estado_*.json')
    volcado = {t['id']: t for t in json.loads(archivo.read_text())['tareas']}
    assert volcado[corta]['estado'] == 'completada'
    assert volcado[larga]['estado'] == 'cancelada'
    assert volcado[larga]['error'] == 'apagado del sistema'
    assert volcado[en_cola]['estado'] == 'pendiente'


async def test_detener_respeta_el_limite_aunque_la_cola_sea_mas_chica_que_el_pool():
    """Con 3 workers ocupados y una cola de 1 lugar no entran los 3
    centinelas.  El apagado igual tiene que terminar en LIMITE_APAGADO."""
    registro = Registro()

    async def tarea_larga(tarea_id, tipo, params):
        await asyncio.sleep(30)

    pool = Pool(n_workers=3, cola_max=1, registro=registro, ejecutar_tarea=tarea_larga)
    pool.iniciar()
    try:
        for i in range(3):
            registro.registrar(Tarea(id=f't{i}', tipo='esperar', params={}, timeout=60))
            await pool.cola.put(f't{i}')
        while pool.ocupados < 3:
            await asyncio.sleep(0.01)

        t0 = time.perf_counter()
        await asyncio.wait_for(pool.detener(timeout=0.3), timeout=3)
        demora = time.perf_counter() - t0

        assert demora < 1.5
        for i in range(3):
            assert registro.obtener(f't{i}').estado == Estado.CANCELADA
    finally:
        for w in pool._workers:
            w.cancel()
        await asyncio.gather(*pool._workers, return_exceptions=True)


# ---- Volcado previo ---- #

def test_al_arrancar_se_reporta_el_volcado_previo(tmp_path, caplog):
    (tmp_path / 'estado_20261101_120000.json').write_text(json.dumps({
        'tareas': [{'estado': 'completada'}, {'estado': 'completada'}, {'estado': 'pendiente'}],
    }))

    with caplog.at_level(logging.INFO):
        reportar_volcado_previo(str(tmp_path))

    assert 'estado_20261101_120000.json' in caplog.text
    assert 'completada=2' in caplog.text
    assert 'pendiente=1' in caplog.text


def test_sin_volcado_previo_lo_informa_y_no_falla(tmp_path, caplog):
    with caplog.at_level(logging.INFO):
        reportar_volcado_previo(str(tmp_path))

    assert 'No se encontraron volcados previos' in caplog.text

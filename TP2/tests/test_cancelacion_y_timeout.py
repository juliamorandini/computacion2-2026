"""test_cancelacion_y_timeout.py - DELETE en cada estado y timeouts por tarea."""

import asyncio
import time

import pytest

import main
import tareas
from utiles import crear, esperar_estado, esperar_workers_libres, estadisticas


# Tareas que tardan mucho más que lo que dura el test
EN_CURSO = {
    'esperar': {'segundos': 30},
    'descargar': {'urls': ['http://lento/demora?s=30'] * 3},
    'hashear': {'texto': 'x', 'iteraciones': 100_000_000},
}


def _tasks_vivas_de(tarea_id: str) -> list[asyncio.Task]:
    """Tasks que siguen corriendo para esta tarea: el Task interno y los
    hijos del gather de descargar."""
    return [
        t for t in asyncio.all_tasks()
        if t.get_name() == f'tarea-{tarea_id}'
        or t.get_coro().__name__ == '_descargar_una'
    ]


# ---- DELETE ---- #

async def test_delete_de_pendiente_la_cancela_y_el_worker_no_la_ejecuta(levantar):
    async with levantar(WORKERS=1) as c:
        ocupa = await crear(c, 'esperar', {'segundos': 0.3})
        tid = await crear(c, 'esperar', {'segundos': 0.1})

        r = await c.delete(f'/tareas/{tid}')
        assert r.status_code == 200
        assert r.json() == {'id': tid, 'estado': 'cancelada'}

        # Cuando el worker se libera, desencola la cancelada y la saltea
        await esperar_estado(c, ocupa, {'completada'})
        await asyncio.sleep(0.1)
        t = (await c.get(f'/tareas/{tid}')).json()
        assert t['estado'] == 'cancelada'
        assert 'iniciada_en' not in t


@pytest.mark.parametrize('tipo', EN_CURSO)
async def test_delete_en_ejecucion_corta_la_tarea_y_libera_todo(cliente, tipo):
    tid = await crear(cliente, tipo, EN_CURSO[tipo])
    await esperar_estado(cliente, tid, {'ejecutando'})
    await asyncio.sleep(0.2)                 # a mitad de camino

    t0 = time.perf_counter()
    r = await cliente.delete(f'/tareas/{tid}')
    demora = time.perf_counter() - t0

    # La respuesta ya trae el estado final, que es uno de los cinco válidos
    assert r.status_code == 200
    assert r.json() == {'id': tid, 'estado': 'cancelada'}
    assert demora < 1

    t = (await cliente.get(f'/tareas/{tid}')).json()
    assert t['estado'] == 'cancelada'
    assert t['error'] == 'cancelada por el usuario'

    # Sin recursos colgados: worker libre, semáforo completo, sin Tasks huérfanas
    assert (await estadisticas(cliente))['workers_ocupados'] == 0
    assert tareas._semaforo._value == main.MAX_DESCARGAS_SIMULTANEAS
    assert _tasks_vivas_de(tid) == []


async def test_el_worker_sigue_atendiendo_despues_de_una_cancelacion(levantar):
    async with levantar(WORKERS=1) as c:
        tid = await crear(c, 'esperar', {'segundos': 30})
        await esperar_estado(c, tid, {'ejecutando'})
        await c.delete(f'/tareas/{tid}')

        siguiente = await crear(c, 'esperar', {'segundos': 0})
        t = await esperar_estado(c, siguiente, {'completada'})
        assert t['estado'] == 'completada'


async def test_delete_de_completada_devuelve_409(cliente):
    tid = await crear(cliente, 'esperar', {'segundos': 0})
    await esperar_estado(cliente, tid, {'completada'})

    assert (await cliente.delete(f'/tareas/{tid}')).status_code == 409


async def test_delete_de_fallida_devuelve_409(cliente):
    tid = await crear(cliente, 'esperar', {'segundos': 5}, timeout=0.1)
    await esperar_estado(cliente, tid, {'fallida'})

    assert (await cliente.delete(f'/tareas/{tid}')).status_code == 409


async def test_delete_dos_veces_devuelve_409_la_segunda(cliente):
    tid = await crear(cliente, 'esperar', {'segundos': 30})
    await esperar_estado(cliente, tid, {'ejecutando'})

    assert (await cliente.delete(f'/tareas/{tid}')).status_code == 200
    assert (await cliente.delete(f'/tareas/{tid}')).status_code == 409


# ---- Timeout ---- #

@pytest.mark.parametrize('tipo', ['esperar', 'descargar', 'hashear'])
async def test_timeout_vencido_pasa_a_fallida_con_motivo(cliente, tipo):
    tid = await crear(cliente, tipo, EN_CURSO[tipo], timeout=0.3)

    t = await esperar_estado(cliente, tid, {'completada', 'fallida', 'cancelada'})

    assert t['estado'] == 'fallida'
    assert t['error'] == 'timeout de 0.3s excedido'
    await esperar_workers_libres(cliente)
    assert _tasks_vivas_de(tid) == []

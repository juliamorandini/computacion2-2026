"""utiles.py - Helpers para los tests: crear tareas y esperar estados."""

import asyncio
import time

import httpx


async def crear(cliente: httpx.AsyncClient, tipo: str, params: dict, **extra) -> str:
    """Hace POST /tareas y devuelve el id.  Falla si no responde 201."""
    r = await cliente.post('/tareas', json={'tipo': tipo, 'params': params, **extra})
    assert r.status_code == 201, r.text
    return r.json()['id']


async def esperar_estado(
    cliente: httpx.AsyncClient, tarea_id: str, estados: set[str], limite: float = 5.0,
) -> dict:
    """Consulta la tarea hasta que esté en alguno de `estados`.

    Usa asyncio.sleep entre consultas: con time.sleep el loop no podría
    avanzar a los workers y la tarea nunca cambiaría de estado.
    """
    fin = time.monotonic() + limite
    while True:
        tarea = (await cliente.get(f'/tareas/{tarea_id}')).json()
        if tarea['estado'] in estados:
            return tarea
        if time.monotonic() > fin:
            raise AssertionError(
                f'la tarea {tarea_id} quedó en {tarea["estado"]!r}, se esperaba {estados}'
            )
        await asyncio.sleep(0.02)


async def estadisticas(cliente: httpx.AsyncClient) -> dict:
    return (await cliente.get('/estadisticas')).json()


async def esperar_workers_libres(cliente: httpx.AsyncClient, limite: float = 1.0) -> None:
    """Espera a que workers_ocupados llegue a 0.

    Cuando una tarea termina sola (completada o por timeout), su estado
    cambia dentro del Task interno y el worker descuenta 'ocupados' en la
    vuelta siguiente del loop: hay un instante en que se ve una cosa sin
    la otra.
    """
    fin = time.monotonic() + limite
    while (await estadisticas(cliente))['workers_ocupados'] != 0:
        if time.monotonic() > fin:
            raise AssertionError('los workers no se liberaron')
        await asyncio.sleep(0.01)

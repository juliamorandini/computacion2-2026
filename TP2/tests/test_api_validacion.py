"""test_api_validacion.py - Contrato HTTP de la API y validación de entrada."""

import asyncio
import time

import pytest

from utiles import crear, esperar_estado, estadisticas


# ---- POST ---- #

async def test_post_responde_enseguida_aunque_la_tarea_sea_larga(cliente):
    """El POST encola y vuelve: no hace await del trabajo (consigna §1)."""
    t0 = time.perf_counter()
    r = await cliente.post('/tareas', json={'tipo': 'esperar', 'params': {'segundos': 10}})
    demora = time.perf_counter() - t0

    assert r.status_code == 201
    assert r.json()['estado'] == 'pendiente'
    assert demora < 0.05


async def test_post_valido_con_params_por_defecto(cliente):
    r = await cliente.post('/tareas', json={'tipo': 'esperar', 'params': {}})
    assert r.status_code == 201


async def test_post_acepta_urls_http_y_https(cliente):
    r = await cliente.post('/tareas', json={
        'tipo': 'descargar',
        'params': {'urls': ['http://lento/demora', 'https://lento/demora']},
    })
    assert r.status_code == 201


INVALIDOS = [
    ('tipo inexistente', {'tipo': 'volar', 'params': {}}),
    ('urls vacia', {'tipo': 'descargar', 'params': {'urls': []}}),
    ('url sin esquema', {'tipo': 'descargar', 'params': {'urls': ['no-es-url']}}),
    ('url file', {'tipo': 'descargar', 'params': {'urls': ['file:///etc/passwd']}}),
    ('url vacia', {'tipo': 'descargar', 'params': {'urls': ['']}}),
    ('demasiadas urls', {'tipo': 'descargar', 'params': {'urls': ['http://a.com'] * 101}}),
    ('iteraciones cero', {'tipo': 'hashear', 'params': {'texto': 'a', 'iteraciones': 0}}),
    ('iteraciones de mas', {'tipo': 'hashear', 'params': {'texto': 'a', 'iteraciones': 100_000_001}}),
    ('texto muy largo', {'tipo': 'hashear', 'params': {'texto': 'a' * 10_001}}),
    ('segundos negativos', {'tipo': 'esperar', 'params': {'segundos': -1}}),
    ('segundos de mas', {'tipo': 'esperar', 'params': {'segundos': 3601}}),
    ('timeout cero', {'tipo': 'esperar', 'params': {}, 'timeout': 0}),
    ('timeout negativo', {'tipo': 'esperar', 'params': {}, 'timeout': -1}),
    ('timeout de mas', {'tipo': 'esperar', 'params': {}, 'timeout': 3601}),
    ('typo en params de esperar', {'tipo': 'esperar', 'params': {'segundo': 10}}),
    ('typo en params de hashear', {'tipo': 'hashear', 'params': {'texto': 'a', 'iteracione': 5}}),
    ('campo de mas en la tarea', {'tipo': 'esperar', 'params': {}, 'prioridad': 1}),
]


@pytest.mark.parametrize(
    'cuerpo', [c for _, c in INVALIDOS], ids=[nombre for nombre, _ in INVALIDOS],
)
async def test_post_invalido_devuelve_422_y_no_registra_nada(cliente, cuerpo):
    r = await cliente.post('/tareas', json=cuerpo)

    assert r.status_code == 422
    assert (await cliente.get('/tareas')).json() == []


@pytest.mark.parametrize('campo', ['timeout', 'segundos'])
@pytest.mark.parametrize('valor', ['Infinity', 'NaN'])
async def test_numeros_no_finitos_devuelven_422(cliente, campo, valor):
    # Python acepta Infinity y NaN en JSON, así que hay que mandarlos a mano
    if campo == 'timeout':
        cuerpo = f'{{"tipo": "esperar", "params": {{}}, "timeout": {valor}}}'
    else:
        cuerpo = f'{{"tipo": "esperar", "params": {{"segundos": {valor}}}}}'

    r = await cliente.post('/tareas', content=cuerpo, headers={'Content-Type': 'application/json'})

    assert r.status_code == 422


# ---- GET ---- #

async def test_filtro_por_estado_devuelve_solo_ese_estado(levantar):
    async with levantar(WORKERS=1) as c:
        corriendo = await crear(c, 'esperar', {'segundos': 5})
        await esperar_estado(c, corriendo, {'ejecutando'})
        en_cola = await crear(c, 'esperar', {'segundos': 5})

        pendientes = (await c.get('/tareas', params={'estado': 'pendiente'})).json()
        ejecutando = (await c.get('/tareas', params={'estado': 'ejecutando'})).json()

        assert [t['id'] for t in pendientes] == [en_cola]
        assert [t['id'] for t in ejecutando] == [corriendo]


async def test_filtro_por_estado_invalido_devuelve_422(cliente):
    r = await cliente.get('/tareas', params={'estado': 'inventado'})
    assert r.status_code == 422


async def test_get_de_tarea_inexistente_devuelve_404(cliente):
    assert (await cliente.get('/tareas/noexiste')).status_code == 404


async def test_delete_de_tarea_inexistente_devuelve_404(cliente):
    assert (await cliente.delete('/tareas/noexiste')).status_code == 404


# ---- /estadisticas ---- #

async def test_estadisticas_cuenta_estados_y_workers_ocupados(levantar):
    async with levantar(WORKERS=2) as c:
        corta = await crear(c, 'esperar', {'segundos': 0.2})
        larga = await crear(c, 'esperar', {'segundos': 30})
        await esperar_estado(c, corta, {'completada'})
        await esperar_estado(c, larga, {'ejecutando'})

        e = await estadisticas(c)
        assert e['totales']['completada'] == 1
        assert e['totales']['ejecutando'] == 1
        assert e['workers_ocupados'] == 1
        assert e['total_tareas'] == 2

        await c.delete(f'/tareas/{larga}')
        e = await estadisticas(c)
        assert e['totales']['cancelada'] == 1
        assert e['workers_ocupados'] == 0


async def test_tiempo_de_ejecucion_promedio_solo_cuenta_las_completadas(levantar):
    """Una cancelada después de 1 s no debe arrastrar el promedio de las que
    terminaron bien en 0.2 s (mezcladas darían ~0.6 s)."""
    async with levantar(WORKERS=2) as c:
        corta = await crear(c, 'esperar', {'segundos': 0.2})
        larga = await crear(c, 'esperar', {'segundos': 30})
        await esperar_estado(c, corta, {'completada'})
        await asyncio.sleep(1)
        await c.delete(f'/tareas/{larga}')

        tiempos = (await estadisticas(c))['tiempos_promedio']

        assert tiempos['ejecucion'] == pytest.approx(0.2, abs=0.1)
        assert tiempos['espera_en_cola'] < 0.1

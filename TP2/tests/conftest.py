"""conftest.py - Fixtures compartidas de los tests.

La app se levanta con su lifespan real: registro, cola, workers, pool de
procesos y semáforo, igual que en producción.  Los requests van por
httpx.ASGITransport, que llama a FastAPI directo sin abrir un socket.

Dos detalles:
  - ASGITransport no corre el lifespan solo, por eso se entra a mano con
    `async with main.lifespan(main.app)`.
  - Las descargas no salen a la red: el cliente httpx se reemplaza por uno
    con MockTransport que simula un servidor lento.  Así los tests no
    dependen de internet y los tiempos son reproducibles.
"""

import asyncio
import contextlib

import httpx
import pytest

import main
import tareas


# ---- Servidor HTTP falso ---- #

async def _servidor_falso(request: httpx.Request) -> httpx.Response:
    """Simula a servidor_lento: GET /demora?s=X&bytes=N.

    El host 'caido' simula un servidor que no responde (error de conexión).
    """
    if request.url.host == 'caido':
        raise httpx.ConnectError('conexión rechazada', request=request)
    segundos = float(request.url.params.get('s', '0'))
    tamano = int(request.url.params.get('bytes', '100'))
    await asyncio.sleep(segundos)
    return httpx.Response(200, content=b'x' * tamano)


# ---- Fixtures ---- #

@pytest.fixture
def levantar(monkeypatch, tmp_path):
    """Devuelve un context manager que levanta la app con la config dada.

    Uso:
        async with levantar(WORKERS=1, COLA_MAX=2) as cliente:
            await cliente.post('/tareas', json=...)

    Al salir del bloque corre el apagado ordenado del lifespan.
    """

    @contextlib.asynccontextmanager
    async def _levantar(**config):
        config.setdefault('DIR_ESTADO', str(tmp_path))
        # Apagado corto: si un test deja una tarea larga corriendo, el
        # teardown no espera los 10 s de producción.
        config.setdefault('LIMITE_APAGADO', 0.5)
        for nombre, valor in config.items():
            monkeypatch.setattr(main, nombre, valor)

        async with main.lifespan(main.app):
            async with httpx.AsyncClient(
                transport=httpx.MockTransport(_servidor_falso),
            ) as http_falso:
                monkeypatch.setattr(tareas, '_cliente_http', http_falso)
                async with httpx.AsyncClient(
                    transport=httpx.ASGITransport(app=main.app),
                    base_url='http://test',
                ) as cliente:
                    yield cliente

    return _levantar


@pytest.fixture
async def cliente(levantar):
    """La app con la configuración por defecto (4 workers, cola de 100)."""
    async with levantar() as c:
        yield c

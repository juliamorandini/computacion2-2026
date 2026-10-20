"""servidor_lento.py - Servidor HTTP de prueba con latencia configurable.

Responde a GET /demora?s=X esperando X segundos antes de contestar.
Pensado para las mediciones M1 (descargas concurrentes vs secuenciales)
sin depender de internet.

Se levanta como servicio aparte en docker-compose y la API lo alcanza
por el nombre del servicio ('servidor_lento:9000').

Uso:
    python servidor_lento.py          # escucha en 0.0.0.0:9000
    curl http://localhost:9000/demora?s=1
"""

from __future__ import annotations

import asyncio
import os
import logging
from aiohttp import web

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
logger = logging.getLogger(__name__)


async def handle_demora(request: web.Request) -> web.Response:
    """Espera 's' segundos y responde con un payload de texto."""
    try:
        segundos = float(request.query.get('s', '1'))
    except ValueError:
        return web.Response(status=400, text='Parámetro s inválido')

    await asyncio.sleep(segundos)

    # Devuelve un cuerpo de tamaño variable para que haya bytes que medir
    tamano = int(request.query.get('bytes', '1024'))
    cuerpo = 'x' * tamano

    return web.Response(status=200, text=cuerpo)


async def handle_health(request: web.Request) -> web.Response:
    """Health check simple."""
    return web.Response(status=200, text='ok')


def main():
    app = web.Application()
    app.router.add_get('/demora', handle_demora)
    app.router.add_get('/health', handle_health)

    puerto = int(os.getenv('PUERTO', '9000'))
    logger.info('Servidor lento escuchando en 0.0.0.0:%d', puerto)
    web.run_app(app, host='0.0.0.0', port=puerto, print=None)


if __name__ == '__main__':
    main()

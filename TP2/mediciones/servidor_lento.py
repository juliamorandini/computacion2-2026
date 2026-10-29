"""servidor_lento.py - Servidor HTTP de prueba con latencia configurable.

Servidor asyncio puro (sin dependencias externas) que responde a
GET /demora?s=X esperando X segundos antes de contestar.
Pensado para las mediciones M1 (descargas concurrentes vs secuenciales)
sin depender de internet.

Se levanta como servicio aparte en docker-compose y la API lo alcanza
por el nombre del servicio ('servidor_lento:9000').

Uso:
    python servidor_lento.py
    curl http://localhost:9000/demora?s=1
    curl "http://localhost:9000/demora?s=0.5&bytes=4096"
"""

from __future__ import annotations

import asyncio
import logging
import os
from urllib.parse import urlparse, parse_qs

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
logger = logging.getLogger(__name__)


async def _manejar_conexion(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    """Maneja una conexión HTTP entrante.

    Parseo HTTP mínimo: solo lee la primera línea del request (método +
    path) y los headers hasta la línea vacía.  Suficiente para GET.
    """
    try:
        # Leer la línea del request
        linea_request = await asyncio.wait_for(reader.readline(), timeout=10)
        if not linea_request:
            return

        # Leer y descartar los headers
        while True:
            linea = await asyncio.wait_for(reader.readline(), timeout=10)
            if linea == b'\r\n' or linea == b'\n' or not linea:
                break

        # Parsear método y path
        partes = linea_request.decode('utf-8', errors='replace').strip().split(' ')
        if len(partes) < 2:
            await _enviar_respuesta(writer,400, 'Request inválido')
            return

        metodo, ruta_completa = partes[0], partes[1]
        parsed = urlparse(ruta_completa)
        ruta = parsed.path
        query = parse_qs(parsed.query)

        if metodo != 'GET':
            await _enviar_respuesta(writer,405, 'Solo GET')
            return

        if ruta == '/demora':
            await _handle_demora(writer, query)
        elif ruta == '/health':
            await _enviar_respuesta(writer,200, 'ok')
        else:
            await _enviar_respuesta(writer,404, 'No encontrado')

    except (asyncio.TimeoutError, ConnectionError):
        pass
    finally:
        try:
            writer.close()
            await writer.wait_closed()
        except (ConnectionError, OSError):
            pass


async def _handle_demora(writer: asyncio.StreamWriter, query: dict) -> None:
    """Espera 's' segundos y responde con un payload de texto."""
    try:
        segundos = float(query.get('s', ['1'])[0])
    except (ValueError, IndexError):
        await _enviar_respuesta(writer,400, 'Parámetro s inválido')
        return

    tamano = 1024
    try:
        tamano = int(query.get('bytes', ['1024'])[0])
    except (ValueError, IndexError):
        pass

    await asyncio.sleep(segundos)

    cuerpo = 'x' * tamano
    await _enviar_respuesta(writer,200, cuerpo)


async def _enviar_respuesta(writer: asyncio.StreamWriter, status: int, cuerpo: str) -> None:
    """Envía una respuesta HTTP/1.1 mínima.

    write() solo copia al buffer del transporte; drain() espera a que ese
    buffer baje si el cliente lee lento (backpressure, clase 20).
    """
    razones = {200: 'OK', 400: 'Bad Request', 404: 'Not Found', 405: 'Method Not Allowed'}
    razon = razones.get(status, 'Unknown')
    cuerpo_bytes = cuerpo.encode('utf-8')

    respuesta = (
        f'HTTP/1.1 {status} {razon}\r\n'
        f'Content-Type: text/plain; charset=utf-8\r\n'
        f'Content-Length: {len(cuerpo_bytes)}\r\n'
        f'Connection: close\r\n'
        f'\r\n'
    ).encode('utf-8') + cuerpo_bytes

    writer.write(respuesta)
    await writer.drain()


async def main():
    puerto = int(os.getenv('PUERTO', '9000'))

    server = await asyncio.start_server(
        _manejar_conexion,
        host='0.0.0.0',
        port=puerto,
    )
    logger.info('Servidor lento escuchando en 0.0.0.0:%d', puerto)

    async with server:
        await server.serve_forever()


if __name__ == '__main__':
    asyncio.run(main())

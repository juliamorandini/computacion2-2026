"""tareas.py - Dispatch y ejecución de los tres tipos de tarea.

Tres tipos:
  - esperar:   asyncio.sleep (I/O simulado, para probar cancelación).
  - descargar: httpx + asyncio.gather (I/O-bound real, concurrente).
  - hashear:   SHA-256 iterado vía ProcessPoolExecutor en bloques
               (CPU-bound, fuera del event loop).

Las dependencias (httpx client, executor, semáforo) se inyectan con
configurar() desde el lifespan, igual que en api.py.
"""

from __future__ import annotations

import asyncio
import logging
import math
import time
from concurrent.futures import ProcessPoolExecutor
from typing import Any

import httpx

from config import HASH_EN_EXECUTOR, TAMANO_BLOQUE_HASH
from cpu import sha256_bloque

logger = logging.getLogger(__name__)

# ---- Dependencias inyectadas ---- #

_cliente_http: httpx.AsyncClient | None = None
_pool_cpu: ProcessPoolExecutor | None = None
_semaforo: asyncio.Semaphore | None = None


def configurar(
    cliente_http: httpx.AsyncClient,
    pool_cpu: ProcessPoolExecutor,
    semaforo: asyncio.Semaphore,
) -> None:
    """Inyecta las dependencias del módulo.

    Se llama una sola vez en el lifespan, antes de que lleguen tareas.
    """
    global _cliente_http, _pool_cpu, _semaforo
    _cliente_http = cliente_http
    _pool_cpu = pool_cpu
    _semaforo = semaforo


# ---- Dispatch ---- #

async def ejecutar_tarea(tarea_id: str, tipo: str, params: dict[str, Any]) -> Any:
    """Despacha la tarea al handler correcto según su tipo.

    Args:
        tarea_id: Identificador único de la tarea.
        tipo: Uno de 'esperar', 'descargar', 'hashear'.
        params: Parámetros específicos del tipo.

    Returns:
        Resultado de la tarea (serializable a JSON).

    Raises:
        ValueError: Si el tipo no es reconocido.
    """
    handlers = {
        'esperar': _esperar,
        'descargar': _descargar,
        'hashear': _hashear,
    }

    handler = handlers.get(tipo)
    if handler is None:
        raise ValueError(f'Tipo de tarea no reconocido: {tipo!r}')

    return await handler(tarea_id, params)


# ---- esperar ---- #

async def _esperar(tarea_id: str, params: dict) -> dict:
    """Duerme N segundos con asyncio.sleep.

    asyncio.sleep cede el control al event loop (es un punto de suspensión),
    a diferencia de time.sleep que bloquea el hilo entero (clase 18).
    """
    segundos = params.get('segundos', 1)
    logger.info('Tarea %s: esperando %s segundos', tarea_id, segundos)
    await asyncio.sleep(segundos)
    return {'segundos_esperados': segundos}


# ---- descargar ---- #

async def _descargar(tarea_id: str, params: dict) -> dict:
    """Descarga una lista de URLs concurrentemente con httpx + gather.

    Usa asyncio.gather para lanzar todas las descargas a la vez: el
    tiempo total es ~el de la URL más lenta, no la suma (clase 20).

    Un asyncio.Semaphore limita las conexiones simultáneas para no
    agotar descriptores de archivo (mismo patrón que clase 11).

    Si una URL falla, las demás siguen — cada resultado incluye 'error'
    o 'status'+'bytes'+'segundos'.
    """
    urls = params.get('urls', [])
    if not urls:
        raise ValueError('La lista de URLs está vacía')

    logger.info('Tarea %s: descargando %d URLs', tarea_id, len(urls))

    # gather lanza todas en paralelo; return_exceptions=True para que
    # un error en una URL no cancele las demás
    resultados = await asyncio.gather(
        *(
            _descargar_una(url)
            for url in urls
        ),
        return_exceptions=True,
    )

    # Convertir excepciones en dicts de error
    salida = []
    for url, resultado in zip(urls, resultados):
        if isinstance(resultado, Exception):
            salida.append({'url': url, 'error': repr(resultado)})
        else:
            salida.append(resultado)

    return {'descargas': salida}


async def _descargar_una(url: str) -> dict:
    """Descarga una URL individual con control de concurrencia.

    El semáforo se usa con async with, así que se libera incluso si
    la corrutina es cancelada (el __aexit__ se ejecuta durante la
    propagación del CancelledError).
    """
    async with _semaforo:
        inicio = time.perf_counter()
        # async with en la respuesta garantiza que se cierre la conexión
        # si la corrutina es cancelada a mitad de descarga
        async with _cliente_http.stream('GET', url) as respuesta:
            contenido = await respuesta.aread()
            duracion = time.perf_counter() - inicio
            return {
                'url': url,
                'status': respuesta.status_code,
                'bytes': len(contenido),
                'segundos': round(duracion, 4),
            }


# ---- hashear ---- #

async def _hashear(tarea_id: str, params: dict) -> dict:
    """Calcula SHA-256 iterado, ejecutándolo fuera del event loop.

    Se ejecuta en bloques de TAMANO_BLOQUE_HASH iteraciones.  Cada
    bloque va al ProcessPoolExecutor vía run_in_executor, y entre
    bloques hay un await donde la cancelación puede surtir efecto.

    Sin bloques, un Future de proceso no se puede cancelar una vez que
    arrancó (clase 22): la cancelación no tendría efecto hasta que
    termine todo el cómputo.  Con bloques, la demora máxima hasta que
    la cancelación surte efecto es un bloque (~100 ms).

    Se usa ProcessPoolExecutor y no to_thread por el GIL: varias tareas
    hashear en paralelo se serializarían con threads (clase 21).

    Si HASH_EN_EXECUTOR es False, ejecuta directo en la corrutina
    (bloquea el loop).  Esto existe solo para la medición M2.
    """
    texto = params.get('texto', '')
    iteraciones = params.get('iteraciones', 1000)
    logger.info('Tarea %s: hasheando %d iteraciones (executor=%s)',
                tarea_id, iteraciones, HASH_EN_EXECUTOR)

    h = texto.encode('utf-8')

    if not HASH_EN_EXECUTOR:
        # Modo "sin executor" para la medición M2:
        # bloquea el event loop a propósito para demostrar el efecto
        h = sha256_bloque(h, iteraciones)
        return {
            'hash': h.hex(),
            'iteraciones': iteraciones,
        }

    # Ejecución en bloques con ProcessPoolExecutor
    loop = asyncio.get_running_loop()
    n_bloques = math.ceil(iteraciones / TAMANO_BLOQUE_HASH)

    for i in range(n_bloques):
        # El último bloque puede tener menos iteraciones
        restantes = iteraciones - i * TAMANO_BLOQUE_HASH
        n = min(TAMANO_BLOQUE_HASH, restantes)

        # Cada await es un punto donde la cancelación puede surtir efecto
        h = await loop.run_in_executor(_pool_cpu, sha256_bloque, h, n)

    return {
        'hash': h.hex(),
        'iteraciones': iteraciones,
    }

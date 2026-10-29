"""main.py - Punto de entrada de la plataforma de tareas distribuidas.

Orquesta:
  1. Configuración de logging.
  2. Lifespan de FastAPI: crea registro, cola, pool, httpx client,
     ProcessPoolExecutor y semáforo, y los inyecta en api y tareas.
  3. Manejo de señales: SIGTERM/SIGINT disparan apagado ordenado.
  4. Guarda if __name__ == '__main__' para evitar el bucle de reimportación
     con ProcessPoolExecutor en macOS/Windows (clase 22, consigna §4.1).
"""

from __future__ import annotations

import asyncio
import logging
import os
import signal
from concurrent.futures import ProcessPoolExecutor
from contextlib import asynccontextmanager

import httpx
import uvicorn
from fastapi import FastAPI

from config import (
    WORKERS, COLA_MAX, LIMITE_APAGADO, DIR_ESTADO,
    PROCESOS_CPU, MAX_DESCARGAS_SIMULTANEAS,
)
from registro import Registro
from pool import Pool
from tareas import ejecutar_tarea
from persistencia import volcar_estado, reportar_volcado_previo
from cpu import ignorar_sigint
import api
import tareas as modulo_tareas

# ---- Logging ---- #

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%H:%M:%S',
)
logger = logging.getLogger(__name__)


# ---- Estado global del servidor ---- #

_servidor: uvicorn.Server | None = None
_registro: Registro | None = None
_pool: Pool | None = None
_pool_cpu: ProcessPoolExecutor | None = None
_cliente_http: httpx.AsyncClient | None = None


# ---- Lifespan ---- #

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ciclo de vida de la aplicación.

    Startup:
      - Reporta volcados previos.
      - Crea httpx.AsyncClient (un solo cliente reutilizado, conserva
        pool de conexiones y keep-alive — clase 20).
      - Crea ProcessPoolExecutor con initializer que ignora SIGINT en
        los hijos, para que Ctrl+C no les llegue.
      - Crea asyncio.Semaphore para limitar descargas simultáneas.
      - Crea registro, pool de workers y configura api + tareas.

    Shutdown:
      - Deja de aceptar tareas (POST → 503).
      - Drena el pool de workers con timeout.
      - Vuelca estado a JSON.
      - Cierra httpx client y ProcessPoolExecutor.
    """
    global _registro, _pool, _pool_cpu, _cliente_http

    # Reportar volcado previo (si existe)
    reportar_volcado_previo(DIR_ESTADO)

    # ---- Crear recursos ---- #

    # httpx.AsyncClient: un solo cliente para todas las descargas.
    # Conserva el pool de conexiones TCP y el keep-alive (clase 20).
    # timeout de 30s por request para no colgar indefinidamente.
    cliente_http = httpx.AsyncClient(
        timeout=httpx.Timeout(30.0),
        follow_redirects=True,
    )

    # ProcessPoolExecutor: para tareas CPU-bound (hashear).
    # El initializer ignora SIGINT en los hijos para que solo el padre
    # maneje las señales.  Se usa Process y no Thread por el GIL (clase 21).
    pool_cpu = ProcessPoolExecutor(
        max_workers=PROCESOS_CPU,
        initializer=ignorar_sigint,
    )

    # Semáforo: limita las descargas simultáneas para no agotar
    # descriptores de archivo (mismo patrón que clase 11).
    semaforo = asyncio.Semaphore(MAX_DESCARGAS_SIMULTANEAS)

    # ---- Inyectar dependencias en tareas ---- #
    modulo_tareas.configurar(
        cliente_http=cliente_http,
        pool_cpu=pool_cpu,
        semaforo=semaforo,
    )

    # ---- Crear registro y pool de workers ---- #

    registro = Registro()
    pool = Pool(
        n_workers=WORKERS,
        cola_max=COLA_MAX,
        registro=registro,
        ejecutar_tarea=ejecutar_tarea,
    )

    _registro = registro
    _pool = pool
    _pool_cpu = pool_cpu
    _cliente_http = cliente_http

    # Inyectar dependencias en la API
    api.configurar(registro=registro, cola=pool.cola, pool=pool)

    # Iniciar workers
    pool.iniciar()

    # Instalar señales
    _instalar_senales()

    logger.info(
        'Servidor listo — %d workers, cola max %d, %d procesos CPU, '
        'max %d descargas simultáneas, timeout apagado %ss',
        WORKERS, COLA_MAX, PROCESOS_CPU,
        MAX_DESCARGAS_SIMULTANEAS, LIMITE_APAGADO,
    )

    yield  # ← La aplicación corre aquí

    # ---- Shutdown ---- #
    logger.info('Iniciando apagado ordenado...')
    api.dejar_de_aceptar()

    # Detener pool de workers (drena tareas con timeout)
    await pool.detener(timeout=LIMITE_APAGADO)

    # Volcar estado a JSON.  Escribir un archivo es I/O de disco bloqueante:
    # se manda a un thread para no congelar el loop mientras se cierra.
    await asyncio.to_thread(volcar_estado, registro, DIR_ESTADO)

    # Cerrar httpx client
    await cliente_http.aclose()
    logger.info('Cliente httpx cerrado')

    # Cerrar ProcessPoolExecutor (wait=False para no bloquear el loop)
    pool_cpu.shutdown(wait=False, cancel_futures=True)
    logger.info('ProcessPoolExecutor cerrado')

    logger.info('Apagado completo')


# ---- Señales ---- #

def _instalar_senales() -> None:
    """Instala handlers de SIGTERM y SIGINT.

    En Unix usa loop.add_signal_handler (más limpio, no interrumpe el loop).
    En Windows usa signal.signal con un flag (consigna §4.1).
    """
    loop = asyncio.get_running_loop()

    if os.name != 'nt':
        # Unix: add_signal_handler (clase 20)
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, _on_senal, sig)
        logger.info('Señales instaladas con add_signal_handler (Unix)')
    else:
        # Windows: signal.signal (fallback)
        for sig in (signal.SIGTERM, signal.SIGINT):
            signal.signal(sig, lambda s, f: _on_senal(s))
        logger.info('Señales instaladas con signal.signal (Windows)')


def _on_senal(sig) -> None:
    """Handler de señal: pide a uvicorn que se detenga."""
    nombre = signal.Signals(sig).name if isinstance(sig, int) else str(sig)
    logger.info('Señal %s recibida, iniciando apagado...', nombre)

    if _servidor is not None:
        _servidor.should_exit = True


# ---- App ---- #

app = FastAPI(
    title='Plataforma de Tareas Distribuidas',
    description='TP2 — Computación II — Universidad de Mendoza',
    version='1.0.0',
    lifespan=lifespan,
)
app.include_router(api.router)


# ---- Punto de entrada ---- #

if __name__ == '__main__':
    # La guarda __main__ es obligatoria: sin ella, en macOS/Windows el
    # ProcessPoolExecutor (que usa spawn) re-importa este módulo y entra
    # en un bucle infinito de arranques (consigna §4.1).
    # Se pasa el objeto app y no el string 'main:app': con el string uvicorn
    # importa este archivo otra vez como módulo 'main', distinto de
    # '__main__', y _on_senal vería su propio _servidor en None.
    config = uvicorn.Config(
        app=app,
        host='0.0.0.0',
        port=8000,
        log_level='info',
    )
    _servidor = uvicorn.Server(config)
    _servidor.run()

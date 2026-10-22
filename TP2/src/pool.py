"""pool.py - Pool de workers con asyncio.Queue.

Implementa el patrón productor-consumidor (clase 11) con corrutinas:
N workers consumen tareas de una asyncio.Queue compartida.  No hace
falta Lock porque el event loop no interrumpe entre awaits (clase 20).

Cada worker crea un asyncio.Task interno para la ejecución de la tarea,
así un DELETE cancela ese Task sin matar al worker.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Callable, Awaitable, Any

from modelos import Estado
from registro import Registro

logger = logging.getLogger(__name__)

# Centinela para señalar a los workers que deben terminar (clase 21)
_CENTINELA = object()


class Pool:
    """Pool de N workers corrutinas que consumen de una asyncio.Queue."""

    def __init__(
        self,
        n_workers: int,
        cola_max: int,
        registro: Registro,
        ejecutar_tarea: Callable[[str, str, dict[str, Any]], Awaitable[Any]],
    ):
        self._n_workers = n_workers
        self._registro = registro
        self._ejecutar_tarea = ejecutar_tarea
        self._cola: asyncio.Queue = asyncio.Queue(maxsize=cola_max)
        self._workers: list[asyncio.Task] = []
        self._ocupados = 0

    # ---- Propiedades ---- #

    @property
    def cola(self) -> asyncio.Queue:
        return self._cola

    @property
    def ocupados(self) -> int:
        return self._ocupados

    # ---- Ciclo de vida ---- #

    def iniciar(self) -> None:
        """Lanza los N workers como asyncio.Tasks."""
        for i in range(self._n_workers):
            task = asyncio.create_task(self._worker(i), name=f'worker-{i}')
            task.add_done_callback(self._on_worker_terminado)
            self._workers.append(task)
        logger.info('Pool iniciado con %d workers', self._n_workers)

    async def detener(self, timeout: float) -> None:
        """Apagado ordenado: centinelas + espera con límite."""
        # Vaciamos la cola: las pendientes no se ejecutan, quedan como
        # 'pendiente' en el volcado.  Además deja lugar para los centinelas.
        while not self._cola.empty():
            self._cola.get_nowait()
            self._cola.task_done()

        # Ponemos N centinelas para que cada worker salga del while True
        for _ in range(self._n_workers):
            await self._cola.put(_CENTINELA)

        # Esperamos con límite
        terminados, pendientes = await asyncio.wait(
            self._workers, timeout=timeout,
        )

        # Lo que no terminó se cancela
        for task in pendientes:
            task.cancel('apagado')
            logger.warning('Worker %s cancelado por timeout de apagado', task.get_name())

        # Esperamos que los cancelados terminen de procesar el CancelledError
        if pendientes:
            await asyncio.wait(pendientes, timeout=2)

        logger.info('Pool detenido (%d terminados, %d cancelados)',
                     len(terminados), len(pendientes))

    # ---- Worker ---- #

    async def _worker(self, indice: int) -> None:
        """Corrutina que consume tareas de la cola indefinidamente.

        El while True termina cuando recibe el centinela o cuando el
        Task del worker es cancelado (apagado).
        """
        nombre = f'worker-{indice}'
        logger.info('%s iniciado', nombre)

        while True:
            item = await self._cola.get()

            # Centinela: hora de salir (clase 21)
            if item is _CENTINELA:
                self._cola.task_done()
                logger.info('%s recibió centinela, saliendo', nombre)
                return

            tarea_id = item

            tarea = self._registro.obtener(tarea_id)
            if tarea is None:
                self._cola.task_done()
                continue

            # Si la cancelaron mientras estaba pendiente, la salteamos
            if tarea.estado == Estado.CANCELADA:
                self._cola.task_done()
                logger.info('%s saltea tarea %s (ya cancelada)', nombre, tarea_id)
                continue

            # Marcamos como ejecutando (sin await = atómico en el loop)
            self._registro.marcar_ejecutando(tarea_id)
            self._ocupados += 1

            try:
                # Creamos un Task interno para la ejecución
                # Así DELETE cancela este Task sin matar al worker
                task_interno = asyncio.create_task(
                    self._ejecutar_con_timeout(tarea_id, tarea.tipo, tarea.params, tarea.timeout),
                    name=f'tarea-{tarea_id}',
                )
                tarea.task_interno = task_interno

                await task_interno

            except asyncio.CancelledError:
                # ¿Cancelaron al worker o a la tarea?
                if asyncio.current_task().cancelling() > 0:
                    # Cancelaron al worker (apagado) — relanzamos (clase 20)
                    if tarea.estado == Estado.EJECUTANDO:
                        self._registro.marcar_cancelada(tarea_id, 'apagado del sistema')
                    raise
                # Cancelaron la tarea vía DELETE
                if tarea.estado == Estado.EJECUTANDO:
                    self._registro.marcar_cancelada(tarea_id)
            except Exception as exc:
                # Excepción no capturada — la tarea falla pero el worker sigue
                if tarea.estado == Estado.EJECUTANDO:
                    self._registro.marcar_fallida(tarea_id, repr(exc))
                logger.exception('%s: tarea %s falló con excepción', nombre, tarea_id)
            finally:
                self._ocupados -= 1
                tarea.task_interno = None
                self._cola.task_done()

    async def _ejecutar_con_timeout(
        self, tarea_id: str, tipo: str, params: dict, timeout: float
    ) -> None:
        """Ejecuta la tarea con asyncio.timeout (Python 3.11+)."""
        try:
            async with asyncio.timeout(timeout):
                resultado = await self._ejecutar_tarea(tarea_id, tipo, params)
                # Solo marcamos completada si sigue en EJECUTANDO
                # (podría haber sido cancelada entre el await y aquí)
                tarea = self._registro.obtener(tarea_id)
                if tarea and tarea.estado == Estado.EJECUTANDO:
                    self._registro.marcar_completada(tarea_id, resultado)
        except TimeoutError:
            tarea = self._registro.obtener(tarea_id)
            if tarea and tarea.estado == Estado.EJECUTANDO:
                self._registro.marcar_fallida(
                    tarea_id, f'timeout de {timeout}s excedido'
                )
            logger.warning('Tarea %s excedió timeout de %ss', tarea_id, timeout)

    # ---- Callback de supervisión ---- #

    def _on_worker_terminado(self, task: asyncio.Task) -> None:
        """Si un worker termina inesperadamente, lo loguea.

        Sin este callback, la excepción quedaría guardada en el Task,
        nadie la leería y se perdería un worker en silencio.
        """
        if task.cancelled():
            return
        exc = task.exception()
        if exc is not None:
            logger.error('Worker %s terminó con excepción: %r', task.get_name(), exc)

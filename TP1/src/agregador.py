"""agregador.py - Proceso centralizador del snapshot global.

El ``Agregador`` es el **único** proceso que escribe en el snapshot compartido.
Los analizadores le envían sus resultados a través de una ``Queue`` y él se
encarga de actualizar el ``Manager().dict()`` de forma atómica bajo un único
``Lock``.
"""

from multiprocessing import Process, Queue
import time
from multiprocessing.sharedctypes import Synchronized


class Agregador(Process):
    """
    Proceso que recibe datos de los analizadores por una ``Queue`` y
    actualiza el snapshot global de forma consistente.

    Parameters
    ----------
    snapshot : dict-like
        Diccionario compartido (``Manager().dict()``).
    lock : multiprocessing.Lock
        Lock para proteger actualizaciones compuestas.
    queue : multiprocessing.Queue
        Cola de donde se consumen los mensajes de los analizadores.
    verbose_flag : Synchronized (Value("b"))
        Bandera booleana compartida para activar/desactivar logs.
    """

    def __init__(
        self,
        snapshot,
        lock,
        queue: Queue,
        verbose_flag: Synchronized | None = None,
    ):
        super().__init__()
        self.snapshot = snapshot
        self.lock = lock
        self.queue = queue
        self.verbose_flag = verbose_flag

    def _log(self, msg: str):
        if self.verbose_flag and self.verbose_flag.value:
            print(msg)

    def run(self):
        """Bucle principal del agregador."""
        self._log(f"[Agregador] Iniciado (PID {self.pid})")

        while True:
            try:
                # Bloquea hasta recibir un mensaje.
                mensaje = self.queue.get()

                # Señal de shutdown limpio (None en la queue).
                if mensaje is None:
                    self._log("[Agregador] Señal de fin recibida, terminando.")
                    break

                # Validación básica del mensaje.
                if not isinstance(mensaje, dict):
                    self._log(f"[Agregador] Mensaje ignorado (no es dict): {mensaje}")
                    continue

                vista = mensaje.get("vista")
                datos = mensaje.get("data")

                if vista is None or datos is None:
                    self._log(f"[Agregador] Mensaje mal formado: {mensaje}")
                    continue

                # Actualización atómica: datos + timestamp bajo lock.
                with self.lock:
                    self.snapshot[vista] = datos
                    self.snapshot["timestamps"][vista] = time.time()

                self._log(f"[Agregador] Vista '{vista}' actualizada")

            except Exception as exc:
                # Si ocurre un error inesperado, loggeamos y seguimos para
                # evitar que el agregador muera y deje a los demás procesos
                # sin servicio.
                self._log(f"[Agregador] Error: {exc}")

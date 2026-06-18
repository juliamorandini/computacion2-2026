"""agregador.py - Proceso centralizador del snapshot global.

El ``Agregador`` es el **único** proceso que escribe en el snapshot compartido.
Los analizadores le envían sus resultados a través de una ``Queue`` y él se
encarga de actualizar el ``Manager().dict()`` de forma atómica bajo un único
``Lock``.
"""

from multiprocessing import Process, Queue
import time


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
    """

    def __init__(self, snapshot, lock, queue: Queue):
        super().__init__()
        self.snapshot = snapshot
        self.lock = lock
        self.queue = queue

    def run(self):
        """Bucle principal del agregador."""
        print(f"[Agregador] Iniciado (PID {self.pid})")

        while True:
            try:
                # Bloquea hasta recibir un mensaje.
                mensaje = self.queue.get()

                # Señal de shutdown limpio (None en la queue).
                if mensaje is None:
                    print("[Agregador] Señal de fin recibida, terminando.")
                    break

                # Validación básica del mensaje.
                if not isinstance(mensaje, dict):
                    print(f"[Agregador] Mensaje ignorado (no es dict): {mensaje}")
                    continue

                vista = mensaje.get("vista")
                datos = mensaje.get("data")

                if vista is None or datos is None:
                    print(f"[Agregador] Mensaje mal formado: {mensaje}")
                    continue

                # Actualización atómica: datos + timestamp bajo lock.
                with self.lock:
                    self.snapshot[vista] = datos
                    self.snapshot["timestamps"][vista] = time.time()

                print(f"[Agregador] Vista '{vista}' actualizada")

            except Exception as exc:
                # Si ocurre un error inesperado, loggeamos y seguimos para
                # evitar que el agregador muera y deje a los demás procesos
                # sin servicio.
                print(f"[Agregador] Error: {exc}")

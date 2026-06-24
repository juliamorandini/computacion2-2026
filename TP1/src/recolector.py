"""recolector.py - Proceso que escanea /proc y mantiene la lista de PIDs activos.

El ``Recolector`` corre en un loop independiente, lee los directorios numéricos
de ``/proc`` y publica la lista ordenada de PIDs en el snapshot global.  Cada
analizador leerá esa lista cuando le toque su ciclo de refresh, evitando así
que cada uno tenga que escanear /proc por su cuenta.
"""

import os
import time
from multiprocessing import Process, Event
from multiprocessing.synchronize import Event as EventType
from multiprocessing.sharedctypes import Synchronized


class Recolector(Process):
    """
    Proceso que escanea periódicamente ``/proc`` y actualiza el snapshot
    con la lista de PIDs activos.

    Parameters
    ----------
    snapshot : dict-like
        ``Manager().dict()`` compartido.
    intervalo : float, optional
        Segundos entre scans (default 2.0).
    verbose_flag : Synchronized (Value("b"))
        Bandera booleana compartida para activar/desactivar logs.
    """

    def __init__(
        self,
        snapshot,
        intervalo: float = 2.0,
        verbose_flag: Synchronized | None = None,
    ):
        super().__init__()
        self.snapshot = snapshot
        self.intervalo = intervalo
        self._detener = Event()
        self.verbose_flag = verbose_flag

    def detener(self):
        """Señaliza al proceso que debe terminar su loop."""
        self._detener.set()

    def _log(self, msg: str):
        if self.verbose_flag and self.verbose_flag.value:
            print(msg)

    @staticmethod
    def _listar_pids() -> list[int]:
        """
        Lista todos los directorios numéricos de ``/proc``.

        Returns
        -------
        list[int]
            PIDs ordenados de menor a mayor.  Lista vacía si ``/proc`` no es
            accesible.
        """
        pids: list[int] = []
        try:
            for nombre in os.listdir("/proc"):
                if nombre.isdigit():
                    try:
                        pids.append(int(nombre))
                    except ValueError:  # pragma: no cover
                        continue
        except FileNotFoundError:
            # Estamos en un sistema sin /proc (no debería pasar en Docker).
            pass
        return sorted(pids)

    def run(self):
        """Bucle principal del recolector."""
        self._log(f"[Recolector] Iniciado (PID {self.pid})")

        while not self._detener.is_set():
            pids = self._listar_pids()

            # Publicamos en el snapshot.  Como solo tocamos una clave del
            # Manager.dict(), la operación ya es atómica por el servidor IPC.
            self.snapshot["pids"] = pids
            self.snapshot["timestamps"]["pids"] = time.time()

            # Esperamos a que llegue la próxima iteración o la señal de stop.
            self._detener.wait(timeout=self.intervalo)

        self._log("[Recolector] Finalizando.")

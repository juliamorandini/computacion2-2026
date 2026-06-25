"""analizadores/base.py - Clase base para todos los analizadores del monitor.

Cada analizador concreto hereda de ``BaseAnalizador`` e implementa
:meth:`analizar`.  El bucle principal (:meth:`run`) lee la lista de
PIDs desde el ``snapshot`` compartido, analiza cada uno y envía los
datos al Agregador mediante la ``queue``.

El intervalo de refresco es un :py:class:`~multiprocessing.Value`
compartido, lo que permite que el Display lo modifique en tiempo real
sin necesidad de reiniciar el proceso.
"""

import time
from multiprocessing import Process, Event, Value
from multiprocessing.sharedctypes import Synchronized
from typing import Optional


class BaseAnalizador(Process):
    """Proceso analizador base para una vista del monitor.

    Parameters
    ----------
    snapshot :
        ``Manager().dict()`` compartido que contiene ``"pids"``, etc.
    queue :
        Cola hacia la que se envían los resultados para el Agregador.
    nombre_vista : str
        Clave que identifica la vista en el snapshot
        (ej. ``"resumen"``, ``"memoria"``, ...).
    intervalo_inicial : float
        Segundos entre refrescos (por defecto ``2.0``).
    verbose_flag : Synchronized (Value("b")), optional
        Bandera booleana compartida para activar/desactivar logs.
    """

    def __init__(
        self,
        snapshot,
        queue,
        nombre_vista: str,
        intervalo_inicial: float = 2.0,
        verbose_flag: Synchronized | None = None,
    ):
        super().__init__()
        self.snapshot = snapshot
        self.queue = queue
        self.nombre_vista = nombre_vista
        # Value compartido: permite que el Display modifique el intervalo
        # en caliente sin necesidad de reiniciar el proceso.
        self.intervalo = Value("d", intervalo_inicial)
        self._detener = Event()
        self._tiempo_anterior = time.time()
        self.verbose_flag = verbose_flag

    # --------------------------------------------------------------------- #
    # Control de ciclo de vida
    # --------------------------------------------------------------------- #

    def _log(self, msg: str):
        if self.verbose_flag and self.verbose_flag.value:
            print(msg)

    def detener(self):
        """Señaliza al proceso que debe terminar el bucle principal."""
        self._detener.set()

    def _limpiar_caches(self, pids_actuales: list[int]):
        """
        Hook para que subclases limpien caches de PIDs/TIDs que ya no existen.
        Por defecto no hace nada.
        """
        pass

    def run(self):
        """Bucle principal del analizador.

        1. Obtiene la lista de PIDs activos desde ``snapshot["pids"]``.
        2. Llama a :meth:`analizar` para cada PID.
        3. Empaqueta y envía los datos al Agregador.
        4. Duerme el intervalo configurado (ajustable en tiempo real).
        """
        while not self._detener.is_set():
            # Delta real entre iteraciones (útil para cálculos de %CPU).
            ahora = time.time()
            self._delta_t = ahora - self._tiempo_anterior
            self._tiempo_anterior = ahora

            pids = self.snapshot.get("pids", [])
            # Limpiar caches de PIDs que ya no están vivos
            self._limpiar_caches(pids)

            vista_data: dict = {}

            for pid in pids:
                try:
                    dato = self.analizar(pid)
                    if dato is not None:
                        vista_data[pid] = dato
                except Exception:
                    # Los procesos efímeros o sin permisos aparecen y
                    # desaparecen; no interrumpimos el ciclo por ellos.
                    pass

            # Enviar al Agregador (ignorar si la cola está cerrada).
            try:
                self.queue.put({"vista": self.nombre_vista, "data": vista_data})
            except Exception:
                break

            # Dormir el intervalo ajustable; se despierta temprano si
            # llega la señal de detener.
            self._detener.wait(timeout=self.intervalo.value)

    # --------------------------------------------------------------------- #
    # Hook para las subclases
    # --------------------------------------------------------------------- #

    def analizar(self, pid: int) -> Optional[dict]:
        """Analiza un único PID y devuelve sus datos.

        .. note::
            Debe ser implementado por cada subclase concreta.

        Parameters
        ----------
        pid : int
            Identificador del proceso a analizar.

        Returns
        -------
        dict | None
            Diccionario con los datos extraídos de ``/proc/<pid>/``, ó
            ``None`` si el proceso no existe o no se pueden leer sus
            datos.
        """
        raise NotImplementedError(
            "Las subclases deben implementar el método analizar()"
        )
"""analizadores/resumen.py - Analizador de vista Resumen.

Extrae los datos básicos de cada proceso: PID, PPID, estado, número de
threads, UID/GID, usuario, línea de comandos y porcentaje de CPU.
"""

import os
import time
from analizadores.base import BaseAnalizador
from procfs import leer_stat, leer_status, leer_cmdline, uid_a_usuario
from multiprocessing.sharedctypes import Synchronized


class AnalizadorResumen(BaseAnalizador):
    """
    Analizador de la vista *Resumen*.
    """

    def __init__(
        self,
        snapshot,
        queue,
        intervalo_inicial: float = 2.0,
        verbose_flag: Synchronized | None = None,
    ):
        super().__init__(snapshot, queue, "resumen", intervalo_inicial, verbose_flag)
        # Cache local para cálculo de delta de CPU (jiffies).
        # Guardamos tupla: (total_jiffies, timestamp)
        self._prev_cpu: dict[int, tuple[int, float]] = {}

    def _limpiar_caches(self, pids_actuales: list[int]):
        """Elimina del cache _prev_cpu los PIDs que ya no están activos."""
        vivos = set(pids_actuales)
        self._prev_cpu = {pid: v for pid, v in self._prev_cpu.items() if pid in vivos}

    # ----------------------------------------------------------------- #
    # Helpers de parseo (status puede devolver strings para Uid/Gid)
    # ----------------------------------------------------------------- #

    @staticmethod
    def _parsear_uid(status: dict) -> int | None:
        uid = status.get("Uid")
        if uid is None:
            return None
        if isinstance(uid, int):
            return uid
        # "1000    1000    1000    1000"
        try:
            return int(str(uid).split()[0])
        except (ValueError, IndexError):
            return None

    @staticmethod
    def _parsear_gid(status: dict) -> int | None:
        gid = status.get("Gid")
        if gid is None:
            return None
        if isinstance(gid, int):
            return gid
        try:
            return int(str(gid).split()[0])
        except (ValueError, IndexError):
            return None

    # ----------------------------------------------------------------- #
    # Hook requerido por BaseAnalizador
    # ----------------------------------------------------------------- #

    def analizar(self, pid: int) -> dict | None:
        """
        Procesa un único PID y devuelve sus datos de resumen.
        """
        stat = leer_stat(pid)
        status = leer_status(pid)
        cmdline = leer_cmdline(pid)

        if not stat or not status:
            return None

        # -- Datos de /proc/<pid>/stat ---------------------------------
        ppid = stat.get("ppid")
        estado = stat.get("state")
        threads = stat.get("num_threads")

        utime = stat.get("utime", 0)
        stime = stat.get("stime", 0)

        # -- Datos de /proc/<pid>/status -------------------------------
        uid = self._parsear_uid(status)
        gid = self._parsear_gid(status)
        usuario = uid_a_usuario(uid) if uid is not None else None

        # -- CPU% (delta de jiffies con tiempo real por PID) -------------
        total = utime + stime
        ahora = time.time()

        if pid in self._prev_cpu:
            prev_total, prev_time = self._prev_cpu[pid]
            delta_jiffies = total - prev_total
            delta_t_real = ahora - prev_time
            if delta_t_real > 0 and delta_jiffies > 0:
                try:
                    clk_tck = os.sysconf("SC_CLK_TCK")
                except (ValueError, AttributeError):
                    clk_tck = 100
                cpu_pct = 100.0 * delta_jiffies / (clk_tck * delta_t_real)
            else:
                cpu_pct = 0.0
        else:
            # Primera vez que vemos este PID: no hay delta, retornamos 0
            cpu_pct = 0.0

        # Actualizar cache SIEMPRE (incluso en primera vez)
        self._prev_cpu[pid] = (total, ahora)

        return {
            "pid": pid,
            "ppid": ppid,
            "estado": estado,
            "threads": threads,
            "uid": uid,
            "gid": gid,
            "usuario": usuario,
            "cmdline": cmdline,
            "cpu_pct": round(cpu_pct, 2),
        }
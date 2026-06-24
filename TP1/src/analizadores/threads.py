"""analizadores/threads.py - Analizador de vista Threads (LWPs).

Lista los threads de cada proceso, con su TID, nombre, estado y
cantidad de CPU usada (delta de jiffies entre lecturas).
"""

import os
from analizadores.base import BaseAnalizador
from procfs import leer_task
from multiprocessing.sharedctypes import Synchronized


class AnalizadorThreads(BaseAnalizador):
    """Analizador de la vista *Threads*."""

    def __init__(
        self,
        snapshot,
        queue,
        intervalo_inicial: float = 2.0,
        verbose_flag: Synchronized | None = None,
    ):
        super().__init__(snapshot, queue, "threads", intervalo_inicial, verbose_flag)
        # Cache para delta de CPU por TID: {tid: (utime, stime)}
        self._prev_cpu = {}

    def analizar(self, pid: int) -> list | None:
        """
        Retorna lista de threads para un PID, cada uno con:
        - tid: int
        - nombre: str
        - estado: str
        - cpu_pct: float (porcentaje de CPU en este intervalo)
        """
        tids = leer_task(pid)
        if tids is None:
            return None

        threads = []
        for tid in tids:
            datos = self._analizar_thread(pid, tid)
            if datos:
                threads.append(datos)

        return threads

    def _analizar_thread(self, pid: int, tid: int) -> dict | None:
        stat_path = f"/proc/{pid}/task/{tid}/stat"
        comm_path = f"/proc/{pid}/task/{tid}/comm"

        try:
            with open(stat_path, "r") as f:
                contenido = f.read()
        except (FileNotFoundError, PermissionError, ProcessLookupError):
            return None

        # Parseo simplicado de stat (campo comm entre paréntesis)
        primer_paren = contenido.find("(")
        ultimo_paren = contenido.rfind(")")
        if primer_paren == -1 or ultimo_paren == -1:
            return None

        resto = contenido[ultimo_paren + 1 :].split()
        # resto[0] = state, resto[11] = utime, resto[12] = stime
        estado = resto[0] if len(resto) > 0 else "17"
        utime = int(resto[11]) if len(resto) > 11 else 0
        stime = int(resto[12]) if len(resto) > 12 else 0

        # Leer nombre del thread
        try:
            with open(comm_path, "r") as f:
                nombre = f.read().strip()
        except Exception:
            nombre = "<unknown>"

        # Calcular CPU% con delta
        total_cpu = utime + stime
        cpu_pct = 0.0
        if tid in self._prev_cpu:
            prev = self._prev_cpu[tid]
            delta = total_cpu - prev
            if delta > 0:
                # Delta de jiffies a porcentaje
                delta_t = getattr(self, "_delta_t", self.intervalo.value)
                try:
                    clk_tck = os.sysconf("SC_CLK_TCK")
                except (ValueError, AttributeError):
                    clk_tck = 100
                cpu_pct = 100.0 * delta / (clk_tck * delta_t) if delta_t > 0 else 0.0
        self._prev_cpu[tid] = total_cpu

        return {
            "tid": tid,
            "nombre": nombre,
            "estado": estado,
            "cpu_pct": round(cpu_pct, 2),
        }

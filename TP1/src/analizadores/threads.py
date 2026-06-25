"""analizadores/threads.py - Analizador de vista Threads (LWPs).

Lista los threads de cada proceso, con su TID, nombre, estado y
cantidad de CPU usada (delta de jiffies entre lecturas).
"""

import os
import time
from analizadores.base import BaseAnalizador
from procfs import leer_task, leer_status, leer_task_status
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
        # Cache para delta de CPU por TID: {tid: (total_jiffies, timestamp)}
        self._prev_cpu: dict[int, tuple[int, float]] = {}

    def _limpiar_caches(self, pids_actuales: list[int]):
        """
        Elimina del cache _prev_cpu los TIDs de procesos que ya no existen.
        Como no tenemos la lista de TIDs vivos fácilmente, limpiamos de forma conservadora:
        si el PID padre no está en pids_actuales, borramos todos sus TIDs.
        """
        vivos = set(pids_actuales)
        # El cache puede tener TIDs de muchos PIDs; para simplificar,
        # limitamos el tamaño máximo del cache.
        if len(self._prev_cpu) > 5000:
            # Borramos los más antiguos (por timestamp) si crece demasiado
            items = sorted(self._prev_cpu.items(), key=lambda x: x[1][1])
            self._prev_cpu = dict(items[-2500:])

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

        # Calcular CPU% con delta (tiempo real por TID)
        total_cpu = utime + stime
        ahora = time.time()
        cpu_pct = 0.0

        if tid in self._prev_cpu:
            prev_total, prev_time = self._prev_cpu[tid]
            delta_jiffies = total_cpu - prev_total
            delta_t_real = ahora - prev_time
            if delta_t_real > 0 and delta_jiffies > 0:
                try:
                    clk_tck = os.sysconf("SC_CLK_TCK")
                except (ValueError, AttributeError):
                    clk_tck = 100
                cpu_pct = 100.0 * delta_jiffies / (clk_tck * delta_t_real)
                cpu_pct = min(cpu_pct, 100.0)  # cap a 100%
            else:
                cpu_pct = 0.0
        else:
            cpu_pct = 0.0

        # Actualizar cache SIEMPRE
        self._prev_cpu[tid] = (total_cpu, ahora)

        # Context switches del thread (de /proc/<pid>/task/<tid>/status)
        status = leer_task_status(pid, tid)
        voluntary_ctxt = status.get("voluntary_ctxt_switches") if status else None
        nonvoluntary_ctxt = status.get("nonvoluntary_ctxt_switches") if status else None

        return {
            "tid": tid,
            "nombre": nombre,
            "estado": estado,
            "cpu_pct": round(cpu_pct, 2),
            "voluntary_ctxt_switches": voluntary_ctxt,
            "nonvoluntary_ctxt_switches": nonvoluntary_ctxt,
        }

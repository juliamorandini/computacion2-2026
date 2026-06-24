"""analizadores/scheduling.py - Analizador de vista Scheduling.

Extrae datos de planificación de cada proceso: nice, priority,
política de scheduling, RT priority, CPU affinity y context switches.
"""

from analizadores.base import BaseAnalizador
from procfs import leer_stat, leer_status
from multiprocessing.sharedctypes import Synchronized


class AnalizadorScheduling(BaseAnalizador):
    """Analizador de la vista *Scheduling*."""

    # Mapeo de códigos de política de scheduling (campo 41 de /proc/<pid>/stat)
    SCHED = {
        0: "SCHED_OTHER",
        1: "SCHED_FIFO",
        2: "SCHED_RR",
        3: "SCHED_BATCH",
        5: "SCHED_IDLE",
    }

    def __init__(
        self,
        snapshot,
        queue,
        intervalo_inicial: float = 10.0,
        verbose_flag: Synchronized | None = None,
    ):
        super().__init__(snapshot, queue, "scheduling", intervalo_inicial, verbose_flag)

    def analizar(self, pid: int) -> dict | None:
        stat = leer_stat(pid)
        status = leer_status(pid)
        if not stat:
            return None

        # Scheduling policy (campo 41 en /proc stat 0-indexado -> índice 41)
        # Nota: _parsear_stat de procfs.py no extrae campo 40/41, pero status puede tener info.
        policy_code = stat.get("policy")  # Si existe en nuestro parser
        policy = self.SCHED.get(policy_code, "unknown") if policy_code is not None else "unknown"

        # Context switches (voluntarios e involuntarios)
        vol_ctxt = status.get("voluntary_ctxt_switches") if status else None
        nonvol_ctxt = status.get("nonvoluntary_ctxt_switches") if status else None

        # CPU affinity (lista de CPUs permitidas)
        cpus_allowed = status.get("Cpus_allowed_list") if status else None

        return {
            "nice": stat.get("nice"),
            "priority": stat.get("priority"),
            "policy": policy,
            "rt_priority": stat.get("rt_priority"),
            "cpus_allowed_list": cpus_allowed,
            "voluntary_ctxt_switches": vol_ctxt,
            "nonvoluntary_ctxt_switches": nonvol_ctxt,
            "utime": stat.get("utime"),
            "stime": stat.get("stime"),
            "session": stat.get("session"),
            "pgrp": stat.get("pgrp"),
        }

"""analizadores/sistema.py - Analizador de vista Sistema.

Extrae estadísticas globales del sistema: CPU, memoria, load average,
totales de procesos/threads, boot time, uptime, y top 3 por CPU/memoria.
Lee archivos globales de /proc, NO por PID.
"""

import os
from analizadores.base import BaseAnalizador
from multiprocessing.sharedctypes import Synchronized


class AnalizadorSistema(BaseAnalizador):
    """Analizador de la vista *Sistema* (stats globales)."""

    def __init__(
        self,
        snapshot,
        queue,
        intervalo_inicial: float = 2.0,
        verbose_flag: Synchronized | None = None,
    ):
        super().__init__(snapshot, queue, "sistema", intervalo_inicial, verbose_flag)
        self._prev_cpu_vals = None

    def analizar(self, pid: int) -> dict | None:
        """Esta vista NO itera por PID."""
        if getattr(self, "_ya_devuelto", False):
            return None
        self._ya_devuelto = True

        return self._recolectar_sistema()

    def _recolectar_sistema(self) -> dict:
        cpu_info = self._leer_cpu_global()
        mem_info = self._leer_meminfo()
        load_info = self._leer_loadavg()
        boot_time = self._leer_btime()
        uptime = self._leer_uptime()
        totales = self._contar_procesos()
        top_cpu, top_mem = self._top_procesos()

        return {
            "cpu": cpu_info,
            "memoria": mem_info,
            "load": load_info,
            "boot_time": boot_time,
            "uptime": uptime,
            "totales": totales,
            "top_cpu": top_cpu,
            "top_mem": top_mem,
        }

    # ----------------------------------------------------------------- #
    # Helpers de /proc globales
    # ----------------------------------------------------------------- #

    def _leer_cpu_global(self) -> dict:
        """Lee /proc/stat línea 'cpu' y calcula deltas para %CPU."""
        try:
            with open("/proc/stat", "r") as f:
                for linea in f:
                    if linea.startswith("cpu "):
                        partes = linea.split()
                        vals = list(map(int, partes[1:11]))
                        break
        except Exception:
            return {}

        user, nice, system, idle, iowait, irq, softirq, steal, guest, guest_nice = vals
        ahora = {
            "user": user, "nice": nice, "system": system,
            "idle": idle, "iowait": iowait, "irq": irq,
            "softirq": softirq, "steal": steal,
            "guest": guest, "guest_nice": guest_nice,
        }
        total_ahora = sum(vals)

        # Calcular porcentajes si tenemos lectura anterior
        if self._prev_cpu_vals is not None:
            diff_total = total_ahora - self._prev_cpu_vals["total"]
            if diff_total > 0:
                for k in ("user", "nice", "system", "idle", "iowait"):
                    ahora[f"{k}_pct"] = round(
                        100.0 * (ahora[k] - self._prev_cpu_vals[k]) / diff_total, 2
                    )

        self._prev_cpu_vals = {**ahora, "total": total_ahora}
        return ahora

    @staticmethod
    def _leer_meminfo() -> dict:
        """Lee /proc/meminfo y devuelve dict con campos clave (en KB)."""
        campos_interes = {
            "MemTotal", "MemFree", "MemAvailable", "Buffers",
            "Cached", "SwapCached", "Active", "Inactive",
            "SwapTotal", "SwapFree",
        }
        info = {}
        try:
            with open("/proc/meminfo", "r") as f:
                for linea in f:
                    if ":" not in linea:
                        continue
                    k, v = linea.split(":", 1)
                    k = k.strip()
                    if k in campos_interes:
                        info[k] = int(v.strip().split()[0])
        except Exception:
            pass
        return info

    @staticmethod
    def _leer_loadavg() -> tuple[float, float, float]:
        """Lee /proc/loadavg (1, 5, 15 min)."""
        try:
            with open("/proc/loadavg", "r") as f:
                v = f.read().split()[:3]
                return tuple(map(float, v))
        except Exception:
            return (0.0, 0.0, 0.0)

    @staticmethod
    def _leer_btime() -> int | None:
        """Boot time en /proc/stat."""
        try:
            with open("/proc/stat", "r") as f:
                for linea in f:
                    if linea.startswith("btime"):
                        return int(linea.split()[1])
        except Exception:
            pass
        return None

    @staticmethod
    def _leer_uptime() -> float | None:
        """Uptime desde /proc/uptime."""
        try:
            with open("/proc/uptime", "r") as f:
                return float(f.read().split()[0])
        except Exception:
            return None

    def _contar_procesos(self) -> dict:
        """Cuenta procesos y threads totales usando snapshot['pids']."""
        pids = self.snapshot.get("pids", [])
        total_threads = 0
        for pid in pids:
            try:
                with open(f"/proc/{pid}/stat", "r") as f:
                    partes = f.read().split()
                    if len(partes) > 19:
                        total_threads += int(partes[19])
            except Exception:
                pass
        return {"procesos": len(pids), "threads_totales": total_threads}

    def _top_procesos(self) -> tuple[list, list]:
        """Top 3 por CPU% y RSS desde snapshot."""
        resumen = self.snapshot.get("resumen", {})
        memoria = self.snapshot.get("memoria", {})

        top_cpu = sorted(
            [(pid, d.get("cpu_pct", 0)) for pid, d in resumen.items()],
            key=lambda x: x[1], reverse=True
        )[:3]

        top_mem = sorted(
            [(pid, d.get("vmrss", 0)) for pid, d in memoria.items()],
            key=lambda x: x[1], reverse=True
        )[:3]

        return top_cpu, top_mem

"""analizadores/memoria.py - Analizador de vista Memoria.

Extrae información de memoria de cada proceso: VmSize, VmRSS, VmData,
VmStk, VmExe, VmLib, VmHWM, VmSwap, page faults y segmentos agrupados
(text, data, heap, stack, shared).
"""

from analizadores.base import BaseAnalizador
from procfs import leer_status, leer_stat, leer_maps
from multiprocessing.sharedctypes import Synchronized


class AnalizadorMemoria(BaseAnalizador):
    """
    Analizador de la vista *Memoria*.
    """

    # Campos que nos interesan de /proc/<pid>/status
    CAMPOS_STATUS = [
        "VmSize",   # Tamaño virtual total (KB)
        "VmRSS",    # Resident Set Size (KB)
        "VmData",   # Tamaño de datos (KB)
        "VmStk",    # Tamaño de stack (KB)
        "VmExe",    # Tamaño del ejecutable (KB)
        "VmLib",    # Tamaño de librerías compartidas (KB)
        "VmHWM",    # High Water Mark de RSS (pico máximo)
        "VmSwap",   # Memoria en swap (KB)
    ]

    def __init__(
        self,
        snapshot,
        queue,
        intervalo_inicial: float = 3.0,
        verbose_flag: Synchronized | None = None,
    ):
        super().__init__(snapshot, queue, "memoria", intervalo_inicial, verbose_flag)

    def analizar(self, pid: int) -> dict | None:
        status = leer_status(pid)
        stat = leer_stat(pid)
        maps = leer_maps(pid)

        if not status:
            return None

        # -- Datos básicos de /proc/<pid>/status
        datos = {}
        for campo in self.CAMPOS_STATUS:
            valor = status.get(campo)
            datos[campo.lower()] = valor

        # Page faults (correctos: de /proc/<pid>/stat, no status)
        if stat:
            datos["minflt"] = stat.get("minflt")
            datos["majflt"] = stat.get("majflt")
        else:
            datos["minflt"] = None
            datos["majflt"] = None

        # ----- Segmentos de memoria de /proc/<pid>/maps -----
        if maps:
            datos["segmentos_kb"] = maps.get("totales_kb", {})
            # Top 5 módulos por tamaño
            modulos = maps.get("modulos", {})
            top_modulos = sorted(modulos.items(), key=lambda x: x[1], reverse=True)[:5]
            datos["top_modulos"] = top_modulos

        return datos

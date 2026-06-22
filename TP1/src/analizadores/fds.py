"""analizadores/fds.py - Analizador de vista File Descriptors.

Lista los file descriptors abiertos de cada proceso y sus destinos,
con clasificación por tipo (file, pipe, socket, anon, dev, etc.).
"""

from analizadores.base import BaseAnalizador
from procfs import leer_fds


class AnalizadorFDS(BaseAnalizador):
    """Analizador de la vista *File Descriptors*."""

    def __init__(self, snapshot, queue, intervalo_inicial: float = 5.0):
        super().__init__(snapshot, queue, "fds", intervalo_inicial)

    def analizar(self, pid: int) -> list | None:
        """Devuelve lista de dicts con FD, target y tipo."""
        fds = leer_fds(pid)
        return fds

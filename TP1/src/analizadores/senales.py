"""analizadores/senales.py - Analizador de vista Señales.

Extrae las máscaras de señales de cada proceso: bloqueadas (SigBlk),
ignoradas (SigIgn), con handler propio (SigCgt), y pendientes
(SigPnd, ShdPnd). Cada máscara es decodificada a lista de nombres.
"""

from analizadores.base import BaseAnalizador
from procfs import leer_status


class AnalizadorSenales(BaseAnalizador):
    """Analizador de la vista *Señales*."""

    def __init__(self, snapshot, queue, intervalo_inicial: float = 10.0):
        super().__init__(snapshot, queue, "senales", intervalo_inicial)

    def analizar(self, pid: int) -> dict | None:
        """Decodifica las máscaras hex de señales a nombres legibles."""
        status = leer_status(pid)
        if not status:
            return None

        return {
            "sigblk": status.get("SigBlk", []),
            "sigign": status.get("SigIgn", []),
            "sigcgt": status.get("SigCgt", []),
            "sigpnd": status.get("SigPnd", []),
            "shdpnd": status.get("ShdPnd", []),
        }

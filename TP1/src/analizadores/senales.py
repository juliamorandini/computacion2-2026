"""analizadores/senales.py - Analizador de vista Señales.

Extrae las máscaras de señales de cada proceso: bloqueadas (SigBlk),
ignoradas (SigIgn), con handler propio (SigCgt), y pendientes
(SigPnd, ShdPnd). Cada máscara es decodificada a lista de nombres.
"""

from analizadores.base import BaseAnalizador
from procfs import leer_status
from multiprocessing.sharedctypes import Synchronized


class AnalizadorSenales(BaseAnalizador):
    """Analizador de la vista *Señales*."""

    def __init__(
        self,
        snapshot,
        queue,
        intervalo_inicial: float = 10.0,
        verbose_flag: Synchronized | None = None,
    ):
        super().__init__(snapshot, queue, "senales", intervalo_inicial, verbose_flag)

    def analizar(self, pid: int) -> dict | None:
        """Decodifica las máscaras hex de señales a nombres legibles."""
        status = leer_status(pid)
        if not status:
            return None

        default_sig = {"hex": "0000000000000000", "nombres": []}
        return {
            "sigblk": status.get("SigBlk", default_sig),
            "sigign": status.get("SigIgn", default_sig),
            "sigcgt": status.get("SigCgt", default_sig),
            "sigpnd": status.get("SigPnd", default_sig),
            "shdpnd": status.get("ShdPnd", default_sig),
        }

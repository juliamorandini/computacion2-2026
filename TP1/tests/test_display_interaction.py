import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from display import Display


class DummyStopEvent:
    def __init__(self):
        self._set = False

    def is_set(self):
        return self._set

    def set(self):
        self._set = True


class DisplayInteractionTests(unittest.TestCase):
    def test_teclas_de_navegacion_pide_refresh(self):
        display = Display(snapshot={"pids": [], "resumen": {}}, stop_event=DummyStopEvent())
        display._refresh_requested.clear()

        display._procesar_tecla("c")
        self.assertTrue(display._refresh_requested.is_set())

        display._refresh_requested.clear()
        display._procesar_tecla("/")
        self.assertTrue(display._refresh_requested.is_set())


if __name__ == "__main__":
    unittest.main()

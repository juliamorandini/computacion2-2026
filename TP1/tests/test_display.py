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


class DisplayTests(unittest.TestCase):
    def test_render_vista_resumen_no_falla_con_lista_vacia(self):
        snapshot = {"pids": [], "resumen": {}}
        display = Display(snapshot=snapshot, stop_event=DummyStopEvent())

        tabla = display._render_vista_resumen()

        self.assertIsNotNone(tabla)


if __name__ == "__main__":
    unittest.main()

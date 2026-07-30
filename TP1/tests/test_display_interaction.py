import sys
from pathlib import Path
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import display as display_module
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

    def test_mapea_teclas_de_flecha_windows(self):
        display = Display(snapshot={"pids": [], "resumen": {}}, stop_event=DummyStopEvent())

        self.assertEqual(display._normalizar_tecla("\x00", "H"), "up")
        self.assertEqual(display._normalizar_tecla("\x00", "P"), "down")
        self.assertEqual(display._normalizar_tecla("\x00", "M"), "right")
        self.assertEqual(display._normalizar_tecla("\x00", "K"), "left")

    def test_cambia_refresh_sin_analizadores_compartidos(self):
        display = Display(snapshot={"pids": [], "resumen": {}}, stop_event=DummyStopEvent())

        display._ajustar_intervalo_analizador(+0.5)
        self.assertAlmostEqual(display.refresh_rate, 1.5)

        display._ajustar_intervalo_analizador(-0.5)
        self.assertAlmostEqual(display.refresh_rate, 1.0)

    def test_input_loop_no_se_rompe_si_msvcrt_falla(self):
        display = Display(snapshot={"pids": [], "resumen": {}}, stop_event=DummyStopEvent())
        fake_msvcrt = type(
            "FakeMsvcrt",
            (),
            {
                "kbhit": staticmethod(lambda: (_ for _ in ()).throw(OSError("boom"))),
                "getwch": staticmethod(lambda: "x"),
            },
        )

        with patch.dict(sys.modules, {"msvcrt": fake_msvcrt}):
            with patch.object(display_module.time, "sleep", side_effect=KeyboardInterrupt):
                try:
                    display._input_loop()
                except KeyboardInterrupt:
                    pass


if __name__ == "__main__":
    unittest.main()

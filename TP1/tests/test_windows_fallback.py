import sys
from pathlib import Path
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import main


class WindowsFallbackTests(unittest.TestCase):
    def test_actualiza_snapshot_con_varios_procesos(self):
        with patch.object(
            main,
            "_listar_procesos_windows",
            return_value=[
                {"pid": 1, "name": "System", "cmdline": "System"},
                {"pid": 42, "name": "python", "cmdline": "python src/main.py"},
            ],
        ):
            snapshot = {}
            main._actualizar_snapshot_windows(snapshot, 1.0)

        self.assertEqual(snapshot["pids"], [1, 42])
        self.assertEqual(len(snapshot["resumen"]), 2)
        self.assertEqual(snapshot["sistema"]["totales"]["procesos"], 2)


if __name__ == "__main__":
    unittest.main()

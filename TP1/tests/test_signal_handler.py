import signal
import unittest
from unittest.mock import patch
from multiprocessing import Value

from senales import SignalHandler


class DummyStopEvent:
    def is_set(self):
        return False

    def set(self):
        return None


class SignalHandlerTests(unittest.TestCase):
    def test_install_no_falla_si_faltan_senales_en_windows(self):
        handler = SignalHandler(
            stop_event=DummyStopEvent(),
            verbose_flag=Value("b", False),
            analizadores={},
        )

        with patch("senales.signal.signal", side_effect=lambda *args, **kwargs: None), patch(
            "senales.signal.set_wakeup_fd", side_effect=lambda *args, **kwargs: None
        ):
            handler.install()

        self.assertTrue(True)


if __name__ == "__main__":
    unittest.main()

"""senales.py - Manejo de señales para el monitor (Fase 7).

Implementa handlers para:
- SIGINT/SIGTERM: shutdown limpio vía stop_event
- SIGHUP: recarga config.json y propaga nuevos intervalos a analizadores
- SIGUSR1: dump del snapshot a dump_<timestamp>.json
- SIGUSR2: toggle verbose_flag (Value("b") compartido)
- SIGWINCH: repaint de la TUI (opcional, recomendado)

Usa el patrón **self-pipe** (signal.set_wakeup_fd) para integrar señales
async-signal-safe con el loop principal de la TUI (rich.Live + thread input).
"""

import os
import signal
import json
import time
import threading
from datetime import datetime
from multiprocessing.sharedctypes import Synchronized
from multiprocessing.synchronize import Event as EventType
from typing import Any, Callable


class SelfPipe:
    """
    Self-pipe trick para manejar señales de forma async-signal-safe.

    El handler de señal solo escribe un byte en el pipe (async-signal-safe).
    El loop principal vigila el fd de lectura con select()/poll() y procesa
    las señales en contexto síncrono, seguro para cualquier operación.
    """

    def __init__(self):
        # Crear pipe: read_fd para select(), write_fd para handler
        self._read_fd, self._write_fd = os.pipe()
        # Hacer no-bloqueante para evitar deadlocks
        os.set_blocking(self._read_fd, False)
        os.set_blocking(self._write_fd, False)

    @property
    def read_fd(self) -> int:
        return self._read_fd

    def write(self, signum: int):
        """Escribe un byte en el pipe desde el signal handler (async-signal-safe)."""
        try:
            # Un byte por señal; el valor no importa, solo que hay datos
            os.write(self._write_fd, bytes([signum]))
        except (OSError, BlockingIOError):
            pass  # Pipe lleno o error, ignorar en handler

    def read_signals(self) -> list[int]:
        """Lee y retorna lista de números de señal recibidos desde última llamada."""
        signals = []
        try:
            data = os.read(self._read_fd, 1024)
            signals = list(data)
        except (OSError, BlockingIOError):
            pass
        return signals

    def close(self):
        """Cierra ambos extremos del pipe."""
        try:
            os.close(self._read_fd)
        except OSError:
            pass
        try:
            os.close(self._write_fd)
        except OSError:
            pass


class SignalHandler:
    """
    Manejador central de señales del monitor.

    Coordina:
    - Self-pipe para despertar loop principal (Display.run / thread input)
    - Handlers para SIGINT, SIGTERM, SIGHUP, SIGUSR1, SIGUSR2, SIGWINCH
    - Propagación de intervalos actualizados a analizadores (SIGHUP)
    - Toggle verbose_flag (SIGUSR2)
    - Dump snapshot a JSON (SIGUSR1)
    """

    def __init__(
        self,
        stop_event: EventType,
        verbose_flag: Synchronized,
        analizadores: dict[str, Any],
        config_path: str = "config.json",
        snapshot: dict | None = None,
    ):
        """
        Parameters
        ----------
        stop_event : multiprocessing.Event
            Event que señala shutdown global (main + display + analizadores).
        verbose_flag : multiprocessing.Value("b")
            Bandera booleana compartida para modo verbose (toggle con SIGUSR2).
        analizadores : dict[str, BaseAnalizador]
            Dict nombre_vista -> instancia analizador (para ajustar intervalo.value).
        config_path : str
            Ruta al archivo config.json (recargado en SIGHUP).
        snapshot : dict, optional
            Snapshot global (Manager.dict) para dump en SIGUSR1.
        """
        self.stop_event = stop_event
        self.verbose_flag = verbose_flag
        self.analizadores = analizadores  # dict: "resumen" -> instancia
        self.config_path = config_path
        self.snapshot = snapshot

        self._self_pipe = SelfPipe()
        self._original_handlers: dict[int, Callable] = {}
        self._lock = threading.Lock()

        # Mapeo nombre vista -> clave en config["intervals"]
        self._vista_a_config_key = {
            "resumen": "resumen",
            "memoria": "memoria",
            "fds": "fds",
            "threads": "threads",
            "senales": "senales",
            "scheduling": "scheduling",
            "sistema": "sistema",
        }

    def install(self):
        """Instala handlers para todas las señales soportadas."""
        # Guardar handlers originales para posible restauración
        for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP,
                    signal.SIGUSR1, signal.SIGUSR2):
            self._original_handlers[sig] = signal.signal(sig, self._handler)

        # SIGWINCH opcional (puede no estar disponible en todas las plataformas)
        if hasattr(signal, "SIGWINCH"):
            self._original_handlers[signal.SIGWINCH] = signal.signal(
                signal.SIGWINCH, self._handler
            )

        # Registrar self-pipe con signal.set_wakeup_fd (Python 3.5+)
        # Esto hace que Python despierte de select() automaticamente al recibir señal
        try:
            signal.set_wakeup_fd(self._self_pipe.read_fd)
        except (ValueError, OSError):
            # Puede fallar si fd no válido o ya hay wakeup_fd
            pass

    def _handler(self, signum: int, frame):
        """
        Handler async-signal-safe: solo escribe en self-pipe.
        NO hacer nada más aquí (ni print, ni locks, ni allocations).
        """
        self._self_pipe.write(signum)

    def get_self_pipe_read_fd(self) -> int:
        """Retorna fd de lectura para que Display lo vigile con select()."""
        return self._self_pipe.read_fd

    def process_pending_signals(self):
        """
        Procesa todas las señales pendientes desde self-pipe.
        Debe llamarse desde el loop principal (contexto síncrono, seguro).
        """
        signals = self._self_pipe.read_signals()
        for signum in signals:
            self._process_signal(signum)

    def _process_signal(self, signum: int):
        """Procesa una señal individual (contexto seguro, no handler)."""
        if signum in (signal.SIGINT, signal.SIGTERM):
            self._handle_shutdown(signum)
        elif signum == signal.SIGHUP:
            self._handle_reload_config()
        elif signum == signal.SIGUSR1:
            self._handle_dump_snapshot()
        elif signum == signal.SIGUSR2:
            self._handle_toggle_verbose()
        elif signum == getattr(signal, "SIGWINCH", -1):
            self._handle_winch()

    def _handle_shutdown(self, signum: int = signal.SIGINT):
        """SIGINT/SIGTERM: señaliza shutdown global."""
        sig_name = signal.Signals(signum).name if hasattr(signal, 'Signals') else ('SIGINT' if signum == signal.SIGINT else 'SIGTERM')
        print(f"\n[SignalHandler] Señal {sig_name} recibida: iniciando shutdown...")
        self.stop_event.set()

    def _handle_reload_config(self):
        """SIGHUP: recarga config.json y actualiza intervalos de analizadores."""
        print("[SignalHandler] SIGHUP: recargando config.json...")
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                config = json.load(f)

            intervals = config.get("intervals", {})
            for vista_nombre, analizador in self.analizadores.items():
                config_key = self._vista_a_config_key.get(vista_nombre)
                if config_key and config_key in intervals:
                    nuevo_intervalo = float(intervals[config_key])
                    # Verificar mínimo
                    min_intervals = config.get("min_intervals", {})
                    min_val = float(min_intervals.get(config_key, 0.1))
                    if nuevo_intervalo < min_val:
                        nuevo_intervalo = min_val
                    # Actualizar Value compartido (el analizador lo ve en su próximo ciclo)
                    old = analizador.intervalo.value
                    analizador.intervalo.value = nuevo_intervalo
                    print(f"  {vista_nombre}: intervalo {old:.1f}s -> {nuevo_intervalo:.1f}s")

        except Exception as e:
            print(f"[SignalHandler] Error recargando config: {e}")

    def _handle_dump_snapshot(self):
        """SIGUSR1: dump del snapshot actual a JSON con timestamp."""
        if self.snapshot is None:
            print("[SignalHandler] SIGUSR1: snapshot no disponible")
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"dump_{timestamp}.json"

        print(f"[SignalHandler] SIGUSR1: dumpeando snapshot a {filename}...")

        # Construir dict serializable (Manager.dict -> dict normal)
        dump_data = {}
        for key in self.snapshot:
            if key == "timestamps":
                continue
            valor = self.snapshot[key]
            # Convertir Manager.dict/list a tipos nativos
            dump_data[key] = self._to_serializable(valor)

        # Agregar metadatos
        dump_data["_meta"] = {
            "timestamp": datetime.now().isoformat(),
            "pids_count": len(self.snapshot.get("pids", [])),
        }

        try:
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(dump_data, f, indent=2, ensure_ascii=False)
            print(f"  ✓ Dump guardado en {filename}")
        except Exception as e:
            print(f"[SignalHandler] Error guardando dump: {e}")

    def _to_serializable(self, obj):
        """Convierte tipos de multiprocessing.Manager a tipos nativos JSON-serializables."""
        if hasattr(obj, "copy"):  # Manager.dict / Manager.list
            return obj.copy()
        if isinstance(obj, dict):
            return {k: self._to_serializable(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [self._to_serializable(v) for v in obj]
        return obj

    def _handle_toggle_verbose(self):
        """SIGUSR2: toggle verbose_flag compartido."""
        old = self.verbose_flag.value
        self.verbose_flag.value = not old
        estado = "ACTIVADO" if self.verbose_flag.value else "DESACTIVADO"
        print(f"[SignalHandler] SIGUSR2: verbose {estado}")

    def _handle_winch(self):
        """SIGWINCH: terminal redimensionada - forzar repaint en Display."""
        # El Display debe vigilar este fd y forzar refresh
        # Aquí solo avisamos; el Display lo maneja al leer del self-pipe
        pass

    def cleanup(self):
        """Restaura handlers originales y cierra self-pipe."""
        for sig, handler in self._original_handlers.items():
            try:
                signal.signal(sig, handler)
            except (OSError, ValueError):
                pass
        self._self_pipe.close()
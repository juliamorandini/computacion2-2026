"""display.py - Terminal UI (TUI) del monitor de procesos.

Usa ``rich`` para renderizar en vivo las 7 vistas del snapshot.
Características:
- Navegación con teclas 1–7 (q para salir)
- Refresh periódico configurable (+ / -)
- No bloquea los analizadores (lee ``snapshot`` en modo read-only)
"""

from __future__ import annotations

import os
import sys
import time
import threading
from multiprocessing.synchronize import Event

from rich.console import Console
from rich.live import Live
from rich.layout import Layout
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.columns import Columns
from rich import box

# --------------------------------------------------------------------------- #
#  Configuración de vistas
# --------------------------------------------------------------------------- #

VISTAS = [
    "resumen",
    "memoria",
    "fds",
    "threads",
    "senales",
    "scheduling",
    "sistema",
]

NOMBRE_VISTA = {
    "resumen": "Resumen",
    "memoria": "Memoria",
    "fds": "FDS",
    "threads": "Threads",
    "senales": "Señales",
    "scheduling": "Scheduling",
    "sistema": "Sistema",
}

INTERVALO_MIN = 0.1
INTERVALO_MAX = 10.0


# --------------------------------------------------------------------------- #
#  Clase principal
# --------------------------------------------------------------------------- #

class Display:
    """UI en terminal que muestra el snapshot en vivo.

    Corre en un :py:class:`threading.Thread` separado para no
    interferir con los procesos analizadores.

    Parameters
    ----------
    snapshot : Manager().dict()
        Estado compartido con las vistas.
    stop_event : Event
        Evento multiprocessing que señaliza el fin de la aplicación.
    refresh_rate : float
        Segundos entre refrescos de pantalla (por defecto 1.0).
    """

    # Teclas de navegación
    TECLAS_VISTA = {str(i): nombre for i, nombre in enumerate(VISTAS, start=1)}

    def __init__(
        self,
        snapshot,
        stop_event: Event,
        refresh_rate: float = 1.0,
        signal_pipe_fd: int | None = None,
    ):
        self.snapshot = snapshot
        self.stop_event = stop_event
        self.refresh_rate = refresh_rate
        self._vista_idx = 0
        self._lock = threading.Lock()
        self._last_key: str | None = None
        self._console = Console()
        self._signal_pipe_fd = signal_pipe_fd

    # ------------------------------------------------------------------ #
    #  Propiedades / utilidades
    # ------------------------------------------------------------------ #

    @property
    def vista_actual(self) -> str:
        return VISTAS[self._vista_idx]

    def siguiente_vista(self):
        with self._lock:
            self._vista_idx = (self._vista_idx + 1) % len(VISTAS)

    def anterior_vista(self):
        with self._lock:
            self._vista_idx = (self._vista_idx - 1) % len(VISTAS)

    def set_vista(self, idx: int):
        with self._lock:
            self._vista_idx = idx % len(VISTAS)

    # ------------------------------------------------------------------ #
    #  Helpers de datos
    # ------------------------------------------------------------------ #

    def _snapshot_val(self, key: str, default=None):
        return self.snapshot.get(key, default)

    def _fmt_kb(self, val) -> str:
        try:
            kb = int(val)
        except (TypeError, ValueError):
            return "N/A"
        if kb >= 1024 * 1024:
            return f"{kb / (1024 * 1024):.2f} GB"
        if kb >= 1024:
            return f"{kb / 1024:.2f} MB"
        return f"{kb} KB"

    # ------------------------------------------------------------------ #
    #  Renderizado de vistas
    # ------------------------------------------------------------------ #

    def _render_vista_resumen(self) -> Table:
        tabla = Table(
            title="[bold green]Vista: Resumen[/bold green]",
            box=box.SIMPLE_HEAVY,
            expand=True,
        )
        tabla.add_column("PID", justify="right", style="cyan", no_wrap=True)
        tabla.add_column("PPID", justify="right", style="magenta")
        tabla.add_column("Estado", justify="center")
        tabla.add_column("Threads", justify="right")
        tabla.add_column("Usuario", style="yellow")
        tabla.add_column("CPU%", justify="right", style="red")
        tabla.add_column("Cmdline", style="white")

        pids = self._snapshot_val("resumen", {})

        for pid, datos in pids.items():
            tabla.add_row(
                str(pid),
                str(datos.get("ppid", "")),
                datos.get("estado", "?"),
                str(datos.get("threads", "")),
                str(datos.get("usuario", "") or "?"),
                f"{datos.get('cpu_pct', 0):.1f}%",
                (datos.get("cmdline", "") or "")[:60],
            )

        return tabla

    def _render_vista_memoria(self) -> Table:
        tabla = Table(
            title="[bold green]Vista: Memoria[/bold green]",
            box=box.SIMPLE_HEAVY,
            expand=True,
        )
        tabla.add_column("PID", justify="right", style="cyan")
        tabla.add_column("VmSize", justify="right")
        tabla.add_column("VmRSS", justify="right", style="green")
        tabla.add_column("VmData", justify="right")
        tabla.add_column("VmStk", justify="right")
        tabla.add_column("VmSwap", justify="right", style="red")
        tabla.add_column("MinFlt", justify="right")
        tabla.add_column("MajFlt", justify="right")

        pids = self._snapshot_val("memoria", {})
        for pid, datos in pids.items():
            tabla.add_row(
                str(pid),
                self._fmt_kb(datos.get("vmsize"))
                if datos.get("vmsize") is not None else "",
                self._fmt_kb(datos.get("vmrss"))
                if datos.get("vmrss") is not None else "",
                self._fmt_kb(datos.get("vmdata"))
                if datos.get("vmdata") is not None else "",
                self._fmt_kb(datos.get("vmstk"))
                if datos.get("vmstk") is not None else "",
                self._fmt_kb(datos.get("vmswap"))
                if datos.get("vmswap") is not None else "",
                str(datos.get("minflt", "")),
                str(datos.get("majflt", "")),
            )

        return tabla

    def _render_vista_fds(self) -> Table:
        tabla = Table(
            title="[bold green]Vista: File Descriptors[/bold green]",
            box=box.SIMPLE_HEAVY,
            expand=True,
        )
        tabla.add_column("PID", justify="right", style="cyan")
        tabla.add_column("FD", justify="right")
        tabla.add_column("Tipo", style="yellow")
        tabla.add_column("Target", style="white")

        pids = self._snapshot_val("fds", {})
        for pid, datos in pids.items():
            if not isinstance(datos, list):
                continue
            for fd_info in datos[:10]:  # Limitar para no explotar la tabla
                tabla.add_row(
                    str(pid),
                    str(fd_info.get("fd", "")),
                    fd_info.get("type", "?"),
                    fd_info.get("target", "")[:70],
                )
            if len(datos) > 10:
                tabla.add_row("", "", "...", f"... y {len(datos)-10} más")

        return tabla

    def _render_vista_threads(self) -> Table:
        tabla = Table(
            title="[bold green]Vista: Threads[/bold green]",
            box=box.SIMPLE_HEAVY,
            expand=True,
        )
        tabla.add_column("PID", justify="right", style="cyan")
        tabla.add_column("TID", justify="right", style="magenta")
        tabla.add_column("Nombre", style="yellow")
        tabla.add_column("Estado", justify="center")
        tabla.add_column("CPU%", justify="right", style="red")

        pids = self._snapshot_val("threads", {})
        for pid, datos in pids.items():
            if not isinstance(datos, list):
                continue
            for th in datos[:20]:
                tabla.add_row(
                    str(pid),
                    str(th.get("tid", "")),
                    th.get("nombre", ""),
                    th.get("estado", ""),
                    f"{th.get('cpu_pct', 0):.1f}%",
                )
            if len(datos) > 20:
                tabla.add_row("", "", "...", f"... y {len(datos)-20} más")

        return tabla

    def _render_vista_senales(self) -> Table:
        tabla = Table(
            title="[bold green]Vista: Señales[/bold green]",
            box=box.SIMPLE_HEAVY,
            expand=True,
        )
        tabla.add_column("PID", justify="right", style="cyan")
        tabla.add_column("SigBlk", style="red")
        tabla.add_column("SigIgn", style="yellow")
        tabla.add_column("SigCgt", style="green")
        tabla.add_column("SigPnd", style="magenta")

        pids = self._snapshot_val("senales", {})
        for pid, datos in pids.items():
            tabla.add_row(
                str(pid),
                ", ".join(datos.get("sigblk", [])[:8]) or "-",
                ", ".join(datos.get("sigign", [])[:8]) or "-",
                ", ".join(datos.get("sigcgt", [])[:8]) or "-",
                ", ".join(datos.get("sigpnd", [])[:8]) or "-",
            )

        return tabla

    def _render_vista_scheduling(self) -> Table:
        tabla = Table(
            title="[bold green]Vista: Scheduling[/bold green]",
            box=box.SIMPLE_HEAVY,
            expand=True,
        )
        tabla.add_column("PID", justify="right", style="cyan")
        tabla.add_column("Nice", justify="right")
        tabla.add_column("Priority", justify="right")
        tabla.add_column("Policy", style="yellow")
        tabla.add_column("RT Priority", justify="right")
        tabla.add_column("CPU Affinity", style="magenta")
        tabla.add_column("Vol CtxSw", justify="right")
        tabla.add_column("Nonvol CtxSw", justify="right")

        pids = self._snapshot_val("scheduling", {})
        for pid, datos in pids.items():
            tabla.add_row(
                str(pid),
                str(d.get("nice", "")) if (d := datos) and datos.get("nice") is not None else "",
                str(d.get("priority", "")) if (d := datos) and datos.get("priority") is not None else "",
                str(datos.get("policy", "")),
                str(datos.get("rt_priority", "")) if datos.get("rt_priority") is not None else "",
                str(datos.get("cpus_allowed_list", "")) or "-",
                str(datos.get("voluntary_ctxt_switches", ""))
                if datos.get("voluntary_ctxt_switches") is not None else "",
                str(datos.get("nonvoluntary_ctxt_switches", ""))
                if datos.get("nonvoluntary_ctxt_switches") is not None else "",
            )

        return tabla

    def _render_vista_sistema(self) -> Panel:
        datos = self._snapshot_val("sistema", {})

        if not datos:
            return Panel("[dim]Esperando datos del analizador de sistema...[/dim]", title="Sistema")

        # Panel de CPU
        cpu = datos.get("cpu", {})
        cpu_text = Text()
        if "idle_pct" in cpu:
            cpu_text.append(f"Idle: {cpu['idle_pct']:.1f}%\n")
        for k in ("user_pct", "system_pct", "iowait_pct"):
            if k in cpu:
                cpu_text.append(f"{k.replace('_pct','').capitalize()}: {cpu[k]:.1f}%\n")
        panel_cpu = Panel(cpu_text or "N/A", title="[bold green]CPU[/bold green]")

        # Panel de Memoria
        mem = datos.get("memoria", {})
        mem_text = Text()
        for k in ("MemTotal", "MemFree", "MemAvailable"):
            if k in mem:
                mem_text.append(f"{k}: {mem.get(k):,} KB\n")
        panel_mem = Panel(mem_text or "N/A", title="[bold green]Memoria[/bold green]")

        # Panel de Load
        load = datos.get("load", ())
        if load:
            panel_load = Panel(
                f"1 min: {load[0]:.2f}\n5 min: {load[1]:.2f}\n15 min: {load[2]:.2f}",
                title="[bold green]Load Average[/bold green]",
            )
        else:
            panel_load = Panel("N/A", title="[bold green]Load Average[/bold green]")

        # Panel de Totales
        totales = datos.get("totales", {})
        total_text = Text()
        total_text.append(f"Procesos: {totales.get('procesos', '?')}\n")
        total_text.append(f"Threads:  {totales.get('threads_totales', '?')}\n")
        total_text.append(f"Uptime:   {datos.get('uptime', '?')} s")
        panel_totales = Panel(total_text, title="[bold green]Totales[/bold green]")

        return Panel(
            Columns([panel_cpu, panel_mem, panel_load, panel_totales], expand=True),
            title="[bold green]Vista: Sistema[/bold green]",
            border_style="green",
        )

    # ------------------------------------------------------------------ #
    #  Layout principal
    # ------------------------------------------------------------------ #

    def _build_layout(self) -> Layout:
        """Construye el layout completo con header, body y footer."""
        layout = Layout()

        # Header
        vista_nombre = NOMBRE_VISTA.get(self.vista_actual, self.vista_actual).upper()

        # Contar PIDs activos y PIDs con datos en la vista actual
        pids_activos = len(self._snapshot_val("pids", []))
        datos_actual = self._snapshot_val(self.vista_actual, {})
        con_datos = len(datos_actual) if isinstance(datos_actual, dict) else 0

        header_text = (
            f"[bold blue]Monitor de Procesos y Threads[/bold blue]  [dim]|  "
            f"PIDs: {pids_activos}[/dim]  |  "
            f"Vista: [bold yellow]{vista_nombre}[/bold yellow]  [dim]({con_datos} con datos)[/dim]  |  "
            f"Refresh: {self.refresh_rate:.1f}s"
        )
        header = Layout(Panel(header_text, style="on dark_blue"), size=3)

        # Body (vista actual)
        body = self._render_body()

        # Footer con instrucciones
        footer = Layout(
            Panel(
                "[dim]1-7: Cambiar vista  |  q: Salir  |  +/-: Refresh  |  r: Forzar refresh[/dim]",
                style="on dark_blue",
            ),
            size=3,
        )

        layout.split_column(header, body, footer)
        return layout

    def _render_body(self) -> Layout:
        vista = self.vista_actual
        if vista == "resumen":
            return self._render_vista_resumen()
        if vista == "memoria":
            return self._render_vista_memoria()
        if vista == "fds":
            return self._render_vista_fds()
        if vista == "threads":
            return self._render_vista_threads()
        if vista == "senales":
            return self._render_vista_senales()
        if vista == "scheduling":
            return self._render_vista_scheduling()
        if vista == "sistema":
            return self._render_vista_sistema()
        return Table()

    # ------------------------------------------------------------------ #
    #  Input no bloqueante (thread separado)
    # ------------------------------------------------------------------ #

    def _input_loop(self):
        """Lee teclas de stdin y señales del self-pipe en un thread separado."""
        import select
        import termios
        import tty

        old_settings = termios.tcgetattr(sys.stdin)
        stdin_fd = sys.stdin.fileno()

        # FDs a vigilar: stdin + signal pipe (si existe)
        read_fds = [stdin_fd]
        if self._signal_pipe_fd is not None:
            read_fds.append(self._signal_pipe_fd)

        try:
            tty.setcbreak(stdin_fd)
            while not self.stop_event.is_set():
                # select con timeout para no bloquear indefinidamente
                ready, _, _ = select.select(read_fds, [], [], 0.1)
                for fd in ready:
                    if fd == stdin_fd:
                        ch = sys.stdin.read(1)
                        self._procesar_tecla(ch)
                    elif fd == self._signal_pipe_fd:
                        # Señal recibida - procesar y forzar refresh
                        self._procesar_signal_pipe()
        finally:
            termios.tcsetattr(stdin_fd, termios.TCSADRAIN, old_settings)

    def _procesar_tecla(self, ch: str):
        """Procesa una tecla individual (extraído de _input_loop)."""
        if ch in self.TECLAS_VISTA:
            self.set_vista(VISTAS.index(self.TECLAS_VISTA[ch]))
        elif ch == "q":
            self.stop_event.set()
        elif ch in ("\x1b",):  # Escape key sequences
            # Flechas: leer 2 chars más
            import select
            if select.select([sys.stdin], [], [], 0.05)[0]:
                ch2 = sys.stdin.read(1)
                if ch2 == "[" and select.select([sys.stdin], [], [], 0.05)[0]:
                    ch3 = sys.stdin.read(1)
                    if ch3 == "C":  # Right arrow
                        self.siguiente_vista()
                    elif ch3 == "D":  # Left arrow
                        self.anterior_vista()
        elif ch == "+":
            self.refresh_rate = min(INTERVALO_MAX, self.refresh_rate + 0.1)
        elif ch == "-":
            self.refresh_rate = max(INTERVALO_MIN, self.refresh_rate - 0.1)
        # 'r' — no-op: Live ya refresca automáticamente

        self._last_key = ch

    def _procesar_signal_pipe(self):
        """Drena el self-pipe; el SignalHandler principal procesa las señales."""
        # Solo leer y descartar aqui - el SignalHandler en main thread procesa
        # Esto evita que el pipe se llene y bloquee el handler async-signal-safe
        try:
            os.read(self._signal_pipe_fd, 1024)
        except (OSError, BlockingIOError):
            pass
        # Forzar refresh inmediato al recibir señal
        # (rich.Live se actualiza en el próximo ciclo del run loop)

    # ------------------------------------------------------------------ #
    #  Ciclo principal
    # ------------------------------------------------------------------ #

    def run(self):
        """Inicia la TUI y bloquea hasta ``stop_event``."""
        # Arrancar thread de input (solo funciona en Linux/WSL con tty real)
        input_thread = threading.Thread(target=self._input_loop, daemon=True)
        input_thread.start()

        try:
            with Live(
                self._build_layout(),
                console=self._console,
                screen=True,
                refresh_per_second=4,
                transient=True,
            ) as live:
                while not self.stop_event.is_set():
                    live.update(self._build_layout())
                    # Usar select en lugar de sleep para responder a señales/pipe
                    # Timeout = refresh_rate para mantener tasa de refresco
                    import select
                    read_fds = []
                    if self._signal_pipe_fd is not None:
                        read_fds.append(self._signal_pipe_fd)
                    # No agregamos stdin porque ya lo vigila el thread de input

                    if read_fds:
                        ready, _, _ = select.select(read_fds, [], [], self.refresh_rate)
                        if ready:
                            # Señal recibida - procesar inmediatamente y forzar refresh
                            self._procesar_signal_pipe()
                            continue  # refresh inmediato sin esperar refresh_rate
                    else:
                        # Sin signal pipe, usar sleep simple
                        time.sleep(self.refresh_rate)
        except KeyboardInterrupt:
            self.stop_event.set()
        finally:
            self.stop_event.set()

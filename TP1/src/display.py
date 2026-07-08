"""display.py - Terminal UI (TUI) del monitor de procesos.

Usa ``rich`` para renderizar en vivo las 7 vistas del snapshot.
Características:
- Navegación con teclas 1–7 y r/m/f/t/s/p/g
- Navegación lista: ↑↓, Enter (pin), / (filtro nombre), u (filtro usuario), c (orden)
- Refresh periódico configurable (+ / -) que ajusta intervalo del analizador real
- No bloquea los analizadores (lee ``snapshot`` en modo read-only)
"""

from __future__ import annotations

import os
import sys
import time
import threading
from multiprocessing.synchronize import Event
from multiprocessing.sharedctypes import Synchronized

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

# Ordenes disponibles
SORT_MODES = ["cpu", "rss", "pid"]


# --------------------------------------------------------------------------- #
#  Clase principal
# --------------------------------------------------------------------------- #


# --------------------------------------------------------------------------- #
#  Helpers de ordenamiento (module level)
# --------------------------------------------------------------------------- #

def _get_cpu_for_sort(dato) -> float:
    """Obtiene CPU% para sort, funciona con dict o list."""
    if isinstance(dato, dict):
        return dato.get("cpu_pct", 0)
    # vistas con lista (fds, threads): no hay cpu_pct por proceso
    return 0

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
    signal_pipe_fd : int, optional
        File descriptor del self-pipe para recibir señales.
    signal_handler : SignalHandler, optional
        Instancia del manejador de señales para procesar señales pendientes.
    analizador_intervals : dict[str, Synchronized], optional
        Dict vista -> Value("d") compartido para ajustar intervalo en caliente.
    """

    # Teclas de navegación
    TECLAS_VISTA = {str(i): nombre for i, nombre in enumerate(VISTAS, start=1)}
    # Alias de letras según consigna: r/m/f/t/s/p/g
    TECLAS_VISTA_LETRAS = {
        "r": "resumen",
        "m": "memoria",
        "f": "fds",
        "t": "threads",
        "s": "senales",
        "p": "scheduling",
        "g": "sistema",
    }

    def __init__(
        self,
        snapshot,
        stop_event: Event,
        refresh_rate: float = 1.0,
        signal_pipe_fd: int | None = None,
        signal_handler=None,
        analizador_intervals: dict[str, Synchronized] | None = None,
    ):
        self.snapshot = snapshot
        self.stop_event = stop_event
        self.refresh_rate = refresh_rate
        self._vista_idx = 0
        self._lock = threading.Lock()
        self._last_key: str | None = None
        self._console = Console()
        self._signal_pipe_fd = signal_pipe_fd
        self._signal_handler = signal_handler
        self._analizador_intervals = analizador_intervals or {}

        # --- Estado de navegación y filtrado ---
        self._selected_idx: int = 0          # Índice de fila seleccionada
        self._pinned_pid: int | None = None  # PID "pineado" (Enter)
        self._filter_name: str = ""          # Filtro por nombre de comando
        self._filter_user: str = ""          # Filtro por usuario
        self._sort_mode: str = "cpu"         # "cpu" | "rss" | "pid"
        self._filter_mode: str | None = None # "name" | "user" | None (input mode)
        self._filter_buffer: str = ""        # Buffer mientras se escribe filtro

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
    #  Helpers de lista filtrada/ordenada
    # ------------------------------------------------------------------ #

    def _get_vista_data(self) -> dict:
        """Retorna el dict de datos de la vista actual: {pid: datos}."""
        return self._snapshot_val(self.vista_actual, {})

    def _build_filtered_sorted_pids(self) -> list[tuple[int, dict]]:
        """
        Construye lista de (pid, datos) filtrada y ordenada para la vista actual.
        Retorna lista de tuplas lista para renderizar.
        """
        data = self._get_vista_data()
        if not isinstance(data, dict):
            return []

        items = [(pid, datos) for pid, datos in data.items()]

        # Filtrar por nombre de comando
        if self._filter_name:
            filtro = self._filter_name.lower()
            items = [
                (pid, d) for pid, d in items
                if filtro in (d.get("cmdline", "") or "").lower()
            ]

        # Filtrar por usuario
        if self._filter_user:
            filtro = self._filter_user.lower()
            items = [
                (pid, d) for pid, d in items
                if filtro in (str(d.get("usuario", "")) or "").lower()
            ]

        # Ordenar
        if self._sort_mode == "cpu":
            items.sort(key=lambda x: _get_cpu_for_sort(x[1]), reverse=True)
        elif self._sort_mode == "rss":
            # RSS puede estar en vmrss (memoria) o rss (resumen)
            def get_rss(d):
                if isinstance(d, dict):
                    return d.get("vmrss") or d.get("rss") or 0
                # fds, threads: son listas, no hay RSS
                return 0
            items.sort(key=lambda x: get_rss(x[1]), reverse=True)
        elif self._sort_mode == "pid":
            items.sort(key=lambda x: x[0])

        return items


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

        items = self._build_filtered_sorted_pids()
        self._adjust_selected_idx(len(items))

        for row_idx, (pid, datos) in enumerate(items):
            selected = self._is_row_selected(pid, row_idx)
            style = "bold reverse" if selected else ""
            tabla.add_row(
                str(pid),
                str(datos.get("ppid", "")),
                datos.get("estado", "?"),
                str(datos.get("threads", "")),
                str(datos.get("usuario", "") or "?"),
                f"{datos.get('cpu_pct', 0):.1f}%",
                (datos.get("cmdline", "") or "")[:60],
                style=style if selected else None,
            )

        # Indicador de filtro/orden en título
        if self._filter_name or self._filter_user or self._sort_mode != "cpu":
            info = []
            if self._filter_name:
                info.append(f"nombre={self._filter_name}")
            if self._filter_user:
                info.append(f"user={self._filter_user}")
            info.append(f"orden={self._sort_mode}")
            tabla.title = f"[bold green]Vista: Resumen[/bold green]  [dim]({' | '.join(info)})[/dim]"

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

        items = self._build_filtered_sorted_pids()
        self._adjust_selected_idx(len(items))

        for row_idx, (pid, datos) in enumerate(items):
            selected = self._is_row_selected(pid, row_idx)
            style = "bold reverse" if selected else None
            tabla.add_row(
                str(pid),
                self._fmt_kb(datos.get("vmsize")) if datos.get("vmsize") is not None else "",
                self._fmt_kb(datos.get("vmrss")) if datos.get("vmrss") is not None else "",
                self._fmt_kb(datos.get("vmdata")) if datos.get("vmdata") is not None else "",
                self._fmt_kb(datos.get("vmstk")) if datos.get("vmstk") is not None else "",
                self._fmt_kb(datos.get("vmswap")) if datos.get("vmswap") is not None else "",
                str(datos.get("minflt", "")),
                str(datos.get("majflt", "")),
                style=style,
            )

        if self._filter_name or self._filter_user or self._sort_mode != "rss":
            info = []
            if self._filter_name:
                info.append(f"nombre={self._filter_name}")
            if self._filter_user:
                info.append(f"user={self._filter_user}")
            info.append(f"orden={self._sort_mode}")
            tabla.title = f"[bold green]Vista: Memoria[/bold green]  [dim]({' | '.join(info)})[/dim]"

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

        items = self._build_filtered_sorted_pids()
        self._adjust_selected_idx(len(items))

        for row_idx, (pid, datos) in enumerate(items):
            selected = self._is_row_selected(pid, row_idx)
            style = "bold reverse" if selected else None
            if not isinstance(datos, list):
                continue
            for fd_info in datos[:10]:
                tabla.add_row(
                    str(pid),
                    str(fd_info.get("fd", "")),
                    fd_info.get("type", "?"),
                    fd_info.get("target", "")[:70],
                    style=style,
                )
            if len(datos) > 10:
                tabla.add_row("", "", "...", f"... y {len(datos)-10} más", style=style)

        if self._filter_name or self._filter_user or self._sort_mode != "pid":
            info = []
            if self._filter_name:
                info.append(f"nombre={self._filter_name}")
            if self._filter_user:
                info.append(f"user={self._filter_user}")
            info.append(f"orden={self._sort_mode}")
            tabla.title = f"[bold green]Vista: File Descriptors[/bold green]  [dim]({' | '.join(info)})[/dim]"

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

        items = self._build_filtered_sorted_pids()
        self._adjust_selected_idx(len(items))

        for row_idx, (pid, datos) in enumerate(items):
            selected = self._is_row_selected(pid, row_idx)
            style = "bold reverse" if selected else None
            if not isinstance(datos, list):
                continue
            for th in datos[:20]:
                tabla.add_row(
                    str(pid),
                    str(th.get("tid", "")),
                    th.get("nombre", ""),
                    th.get("estado", ""),
                    f"{th.get('cpu_pct', 0):.1f}%",
                    style=style,
                )
            if len(datos) > 20:
                tabla.add_row("", "", "...", f"... y {len(datos)-20} más", style=style)

        if self._filter_name or self._filter_user or self._sort_mode != "cpu":
            info = []
            if self._filter_name:
                info.append(f"nombre={self._filter_name}")
            if self._filter_user:
                info.append(f"user={self._filter_user}")
            info.append(f"orden={self._sort_mode}")
            tabla.title = f"[bold green]Vista: Threads[/bold green]  [dim]({' | '.join(info)})[/dim]"

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

        items = self._build_filtered_sorted_pids()
        self._adjust_selected_idx(len(items))

        for row_idx, (pid, datos) in enumerate(items):
            selected = self._is_row_selected(pid, row_idx)
            style = "bold reverse" if selected else None
            tabla.add_row(
                str(pid),
                ", ".join(datos.get("sigblk", [])[:8]) or "-",
                ", ".join(datos.get("sigign", [])[:8]) or "-",
                ", ".join(datos.get("sigcgt", [])[:8]) or "-",
                ", ".join(datos.get("sigpnd", [])[:8]) or "-",
                style=style,
            )

        if self._filter_name or self._filter_user or self._sort_mode != "pid":
            info = []
            if self._filter_name:
                info.append(f"nombre={self._filter_name}")
            if self._filter_user:
                info.append(f"user={self._filter_user}")
            info.append(f"orden={self._sort_mode}")
            tabla.title = f"[bold green]Vista: Señales[/bold green]  [dim]({' | '.join(info)})[/dim]"

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

        items = self._build_filtered_sorted_pids()
        self._adjust_selected_idx(len(items))

        for row_idx, (pid, datos) in enumerate(items):
            selected = self._is_row_selected(pid, row_idx)
            style = "bold reverse" if selected else None
            tabla.add_row(
                str(pid),
                str(datos.get("nice", "")) if datos.get("nice") is not None else "",
                str(datos.get("priority", "")) if datos.get("priority") is not None else "",
                str(datos.get("policy", "")),
                str(datos.get("rt_priority", "")) if datos.get("rt_priority") is not None else "",
                str(datos.get("cpus_allowed_list", "")) or "-",
                str(datos.get("voluntary_ctxt_switches", ""))
                if datos.get("voluntary_ctxt_switches") is not None else "",
                str(datos.get("nonvoluntary_ctxt_switches", ""))
                if datos.get("nonvoluntary_ctxt_switches") is not None else "",
                style=style,
            )

        if self._filter_name or self._filter_user or self._sort_mode != "pid":
            info = []
            if self._filter_name:
                info.append(f"nombre={self._filter_name}")
            if self._filter_user:
                info.append(f"user={self._filter_user}")
            info.append(f"orden={self._sort_mode}")
            tabla.title = f"[bold green]Vista: Scheduling[/bold green]  [dim]({' | '.join(info)})[/dim]"

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
                "[dim]1-7/r/m/f/t/s/p/g: Vista  |  ↑↓: Navegar  |  Enter: Pin  |  /: Filtrar  |  u: Usuario  |  c: Orden  |  +/-: Int  |  q: Salir  |  h/?: Ayuda[/dim]",
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
        # Modo filtro: si estamos escribiendo un filtro, procesar carácter a carácter
        if self._filter_mode is not None:
            self._procesar_filtro_input(ch)
            return

        # Números 1-7
        if ch in self.TECLAS_VISTA:
            self.set_vista(VISTAS.index(self.TECLAS_VISTA[ch]))
            self._reset_navegacion()
        # Letras r/m/f/t/s/p/g
        elif ch in self.TECLAS_VISTA_LETRAS:
            self.set_vista(VISTAS.index(self.TECLAS_VISTA_LETRAS[ch]))
            self._reset_navegacion()
        elif ch == "q":
            self.stop_event.set()
        elif ch in ("h", "?"):
            self._mostrar_ayuda()
        elif ch in ("\x1b",):  # Escape key sequences - flechas
            # Flechas: leer 2 chars más
            import select
            if select.select([sys.stdin], [], [], 0.05)[0]:
                ch2 = sys.stdin.read(1)
                if ch2 == "[" and select.select([sys.stdin], [], [], 0.05)[0]:
                    ch3 = sys.stdin.read(1)
                    if ch3 == "A":  # Up arrow
                        self._selected_idx = max(0, self._selected_idx - 1)
                        self._pinned_pid = None  # Quitar pin al navegar
                    elif ch3 == "B":  # Down arrow
                        items = self._build_filtered_sorted_pids()
                        self._selected_idx = min(len(items) - 1, self._selected_idx + 1)
                        self._pinned_pid = None
                    elif ch3 == "C":  # Right arrow
                        self.siguiente_vista()
                        self._reset_navegacion()
                    elif ch3 == "D":  # Left arrow
                        self.anterior_vista()
                        self._reset_navegacion()
        elif ch == "\r" or ch == "\n":  # Enter - Pin proceso
            items = self._build_filtered_sorted_pids()
            if items and self._selected_idx < len(items):
                pid, _ = items[self._selected_idx]
                if self._pinned_pid == pid:
                    self._pinned_pid = None  # Despinear
                else:
                    self._pinned_pid = pid
        elif ch == "/":  # Filtrar por nombre
            self._filter_mode = "name"
            self._filter_buffer = ""
        elif ch == "u":  # Filtrar por usuario
            self._filter_mode = "user"
            self._filter_buffer = ""
        elif ch == "c":  # Toggle orden
            idx = SORT_MODES.index(self._sort_mode)
            self._sort_mode = SORT_MODES[(idx + 1) % len(SORT_MODES)]
        elif ch == "+":
            self._ajustar_intervalo_analizador(+0.5)
        elif ch == "-":
            self._ajustar_intervalo_analizador(-0.5)

        self._last_key = ch

    def _reset_navegacion(self):
        """Resetea el estado de navegación al cambiar de vista."""
        self._selected_idx = 0
        self._pinned_pid = None

    def _procesar_filtro_input(self, ch: str):
        """Procesa entrada de texto para filtros (nombre/usuario)."""
        if ch in ("\x1b",):  # Escape - cancelar filtro
            self._filter_mode = None
            self._filter_buffer = ""
        elif ch in ("\r", "\n"):  # Enter - confirmar filtro
            if self._filter_mode == "name":
                self._filter_name = self._filter_buffer
            elif self._filter_mode == "user":
                self._filter_user = self._filter_buffer
            self._filter_mode = None
            self._filter_buffer = ""
            self._reset_navegacion()
        elif ch in ("\x7f", "\x08"):  # Backspace / Delete
            self._filter_buffer = self._filter_buffer[:-1]
        elif len(ch) == 1 and ch.isprintable():
            self._filter_buffer += ch

    def _ajustar_intervalo_analizador(self, delta: float):
        """Ajusta el intervalo del analizador de la vista activa via Value compartido."""
        vista = self.vista_actual
        if vista in self._analizador_intervals:
            intervalo_value = self._analizador_intervals[vista]
            nuevo = max(INTERVALO_MIN, min(INTERVALO_MAX, intervalo_value.value + delta))
            intervalo_value.value = nuevo
            # También actualizar el refresh_rate del display para que coincida aproximadamente
            self.refresh_rate = min(INTERVALO_MAX, max(INTERVALO_MIN, self.refresh_rate + delta))

    def _mostrar_ayuda(self):
        """Muestra pantalla de ayuda (stub - en una TUI real abriría un panel)."""
        # Por ahora solo loggea; idealmente abriría un Panel modal con rich
        print("\n=== AYUDA ===")
        print("1-7 o r/m/f/t/s/p/g: Cambiar vista")
        print("↑ ↓: Navegar lista")
        print("Enter: Pin proceso")
        print("/: Filtrar por nombre")
        print("u: Filtrar por usuario")
        print("c: Toggle orden CPU/RSS/PID")
        print("+/-: Ajustar intervalo")
        print("q: Salir")
        print("h/?: Esta ayuda")
        print("==============\n")

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
                            if self._signal_handler:
                                self._signal_handler.process_pending_signals()
                            continue  # refresh inmediato sin esperar refresh_rate
                    else:
                        # Sin signal pipe, usar sleep simple
                        time.sleep(self.refresh_rate)

                    # Procesar señales pendientes también en cada iteración normal
                    if self._signal_handler:
                        self._signal_handler.process_pending_signals()
        except KeyboardInterrupt:
            self.stop_event.set()
        finally:
            self.stop_event.set()

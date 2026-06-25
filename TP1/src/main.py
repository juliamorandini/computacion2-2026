"""main.py - Punto de entrada del monitor de procesos y threads.

Orquesta:
  1. Creación del estado compartido (snapshot).
  2. Lanzamiento de Recolector y Agregador.
  3. Lanzamiento de los 7 analizadores.
  4. Inicio de la TUI (Display) que muestra datos en vivo.
  5. Shutdown limpio al salir de la TUI.
"""

import signal
import time
import sys
import json
from multiprocessing import Queue, Event, Value

from display import Display
from estado import crear_estado
from agregador import Agregador
from recolector import Recolector
from analizadores.resumen import AnalizadorResumen
from analizadores.memoria import AnalizadorMemoria
from analizadores.fds import AnalizadorFDS
from analizadores.threads import AnalizadorThreads
from analizadores.senales import AnalizadorSenales
from analizadores.scheduling import AnalizadorScheduling
from analizadores.sistema import AnalizadorSistema
from senales import SignalHandler


# --------------------------------------------------------------------------- #
#  Configuración de analizadores: nombre, clase, intervalo_default
# --------------------------------------------------------------------------- #

ANALIZADORES = [
    ("Resumen",    AnalizadorResumen,    2.0),
    ("Memoria",    AnalizadorMemoria,    3.0),
    ("FDS",        AnalizadorFDS,        5.0),
    ("Threads",    AnalizadorThreads,    2.0),
    ("Señales",    AnalizadorSenales,    10.0),
    ("Scheduling", AnalizadorScheduling, 10.0),
    ("Sistema",    AnalizadorSistema,    2.0),
]


def _shutdown_limpio(instancias, agregador, recolector, queue):
    """Envía señales de fin a todos los procesos y espera que terminen."""
    # 1. Detener analizadores
    for nombre, inst in instancias:
        print(f"[Main] Deteniendo Analizador{nombre}...")
        inst.detener()
        inst.join(timeout=5.0)
        if inst.is_alive():
            print(f"  ⚠️  Forzando terminate()...")
            inst.terminate()

    # 2. Detener Agregador
    print("[Main] Deteniendo Agregador...")
    try:
        queue.put(None)
    except Exception:
        pass
    agregador.join(timeout=5.0)
    if agregador.is_alive():
        agregador.terminate()

    # 3. Detener Recolector
    print("[Main] Deteniendo Recolector...")
    recolector.detener()
    recolector.join(timeout=5.0)
    if recolector.is_alive():
        recolector.terminate()

    print("\n[Main] Todos los procesos finalizaron. Fin.")


def _cargar_config(path: str = "config.json") -> dict:
    """Carga configuración desde JSON. Retorna dict con defaults si falla."""
    defaults = {
        "intervals": {
            "resumen": 2.0, "memoria": 3.0, "fds": 5.0,
            "threads": 2.0, "senales": 10.0, "scheduling": 10.0, "sistema": 2.0
        },
        "min_intervals": {
            "resumen": 0.5, "memoria": 1.0, "fds": 2.0,
            "threads": 0.5, "senales": 5.0, "scheduling": 5.0, "sistema": 1.0
        },
        "default_sort": "cpu",
        "verbose": False,
    }
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Merge con defaults por si faltan claves
        for k, v in defaults.items():
            if k not in data:
                data[k] = v
        return data
    except Exception:
        return defaults


def main():
    # Determinar modo
    es_batch = len(sys.argv) > 1 and sys.argv[1] == "--batch"
    es_tui = not es_batch

    if es_batch:
        print("Monitor de Procesos y Threads - TP1 Computación II")
        print("Inicializando...\n")

    # ------------------------------------------------------------------
    # Estado compartido y comunicación IPC
    # ------------------------------------------------------------------
    snapshot, lock, verbose_flag = crear_estado()
    queue = Queue()
    stop_event = Event()

    # ------------------------------------------------------------------
    # Lanzar Recolector y Agregador
    # verbose_flag.value controla logs en todos los procesos
    recolector = Recolector(snapshot, intervalo=2.0, verbose_flag=verbose_flag)
    agregador = Agregador(snapshot, lock, queue, verbose_flag=verbose_flag)

    recolector.start()
    agregador.start()

    # Esperar primera carga de PIDs
    if es_batch:
        print("[Main] Esperando PIDs del Recolector...")
    time.sleep(2.5)

    # ------------------------------------------------------------------
    # Lanzar analizadores
    # ------------------------------------------------------------------
    instancias: list[tuple[str, any]] = []
    for nombre, Clase, intervalo in ANALIZADORES:
        inst = Clase(snapshot, queue, intervalo_inicial=intervalo, verbose_flag=verbose_flag)
        inst.start()
        instancias.append((nombre, inst))
        if es_batch:
            print(f"[Main] Analizador {nombre} iniciado (PID {inst.pid}).")

    # ------------------------------------------------------------------
    # Configurar manejador de señales (solo en modo TUI)
    # ------------------------------------------------------------------
    signal_handler = None
    if es_tui:
        config = _cargar_config()
        # Pasamos la lista de (nombre, instancia) para poder ajustar intervalos
        analizadores_dict = {nombre.lower(): inst for nombre, inst in instancias}
        signal_handler = SignalHandler(
            stop_event=stop_event,
            verbose_flag=verbose_flag,
            analizadores=analizadores_dict,
            config_path="config.json",
            snapshot=snapshot,
        )
        signal_handler.install()

    # ------------------------------------------------------------------
    # Modo batch: espera y muestra snapshot
    # ------------------------------------------------------------------
    if es_batch:
        espera = max(intervalo for _, _, intervalo in ANALIZADORES) + 2.0
        print(f"\n[Main] Modo BATCH: Esperando {espera:.0f}s para que publiquen datos...")
        time.sleep(espera)

        print("\n" + "=" * 60)
        print("[Main] Snapshot actual:")
        print("=" * 60)
        for clave in snapshot:
            if clave == "timestamps":
                continue
            valor = snapshot[clave]
            if not valor:
                print(f"  {clave:20s}: <vacío>")
                continue
            if clave == "resumen" and isinstance(valor, dict):
                print(f"  {clave:20s}: {len(valor)} PIDs")
                top = sorted(valor.items(), key=lambda x: x[1].get("cpu_pct", 0), reverse=True)[:3]
                for pid, datos in top:
                    cmd = (datos.get("cmdline", "") or "")[:30]
                    print(f"      PID {pid}: cpu={datos.get('cpu_pct','?')}%  [{datos.get('estado','?')}]  {cmd}")
            elif clave == "memoria" and isinstance(valor, dict):
                print(f"  {clave:20s}: {len(valor)} PIDs")
                top = sorted(
                    [(pid, d.get("vmrss", 0)) for pid, d in valor.items()],
                    key=lambda x: x[1], reverse=True,
                )[:3]
                for pid, vmrss in top:
                    print(f"      PID {pid}: VmRSS={vmrss} KB")
            elif clave == "sistema" and isinstance(valor, dict):
                cpu = valor.get("cpu", {})
                mem = valor.get("memoria", {})
                load = valor.get("load", ())
                print(f"  {clave:20s}: ---")
                if cpu and "idle_pct" in cpu:
                    print(f"      CPU idle:   {cpu['idle_pct']:.1f}%")
                if mem:
                    print(f"      MemTotal:   {mem.get('MemTotal')} KB")
                if load:
                    print(f"      Load avg:   {load[0]:.2f} / {load[1]:.2f} / {load[2]:.2f}")
            else:
                print(f"  {clave:20s}: {len(valor) if hasattr(valor, '__len__') else '---'}")

        _shutdown_limpio(instancias, agregador, recolector, queue)
        return

    # ------------------------------------------------------------------
    # Modo TUI (por defecto)
    # ------------------------------------------------------------------
    # Pequeño delay para que los analizadores publiquen algo antes de la TUI
    time.sleep(1.0)

    # Instanciar y arrancar la TUI (bloquea hasta que cierra)
    signal_pipe_fd = signal_handler.get_self_pipe_read_fd() if signal_handler else None
    # Construir dict vista -> Value("d") del analizador para ajustes en caliente
    analizador_intervals = {nombre.lower(): inst.intervalo for nombre, inst in instancias}
    display = Display(
        snapshot,
        stop_event,
        refresh_rate=1.0,
        signal_pipe_fd=signal_pipe_fd,
        signal_handler=signal_handler,
        analizador_intervals=analizador_intervals,
    )
    try:
        display.run()
    except KeyboardInterrupt:
        stop_event.set()
    finally:
        stop_event.set()
        if signal_handler:
            signal_handler.cleanup()

    # Al cerrar la TUI, hacer shutdown de todo
    _shutdown_limpio(instancias, agregador, recolector, queue)


if __name__ == "__main__":
    main()

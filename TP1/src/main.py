"""main.py - Punto de entrada del monitor de procesos y threads.

Orquesta la creación del estado compartido, lanza el proceso Recolector,
el Agregador y todos los analizadores concretosZF, espera un tiempo para
que publiquen datos, muestra un resumen del snapshot y finaliza limpiamente.
"""

import time
from multiprocessing import Queue

from estado import crear_estado
from agregador import Agregador
from recolector import Recolector

# Analizadores concretos
from analizadores.resumen import AnalizadorResumen
from analizadores.memoria import AnalizadorMemoria
from analizadores.fds import AnalizadorFDS
from analizadores.threads import AnalizadorThreads
from analizadores.senales import AnalizadorSenales
from analizadores.scheduling import AnalizadorScheduling
from analizadores.sistema import AnalizadorSistema


# --------------------------------------------------------------------------- #
#  Configuración de los analizadores (nombre, clase, intervalo_default)
# --------------------------------------------------------------------------- #

ANALIZADORES = [
    ("Resumen",   AnalizadorResumen,      2.0),	 # bytes: (
    ("Memoria",   AnalizadorMemoria,      3.0),
    ("FDS",       AnalizadorFDS,          5.0),
    ("Threads",   AnalizadorThreads,      2.0),
    ("Señales",   AnalizadorSenales,      10.0),
    ("Scheduling", AnalizadorScheduling,  10.0),
    ("Sistema",   AnalizadorSistema,      2.0),
]


def main():
    print("Monitor de Procesos y Threads - TP1 Computación II\n")

    # ------------------------------------------------------------------
    # FASE 3: Estado compartido
    # ------------------------------------------------------------------
    snapshot, lock = crear_estado()

    # ------------------------------------------------------------------
    # FASE 4: Recolector + Agregador
    # ------------------------------------------------------------------
    queue = Queue()

    recolector = Recolector(snapshot, intervalo=2.0)
    agregador = Agregador(snapshot, lock, queue)

    recolector.start()
    agregador.start()

    # ------------------------------------------------------------------
    # Esperar a que el Recolector publique la primera lista de PIDs
    # ------------------------------------------------------------------
    print("[Main] Esperando a que el Recolector publique PIDs...")
    time.sleep(2.5)

    pids = snapshot.get("pids", [])
    print(f"[Main] Recolector encontró {len(pids)} procesos.")

    # ------------------------------------------------------------------
    # FASE 5: Arrancar todos los analizadores灌顶 concretos
    # ------------------------------------------------------------------
    instancias = []      # guardar referencias para detenerlos luego

    for nombre, Clase, intervalo in ANALIZADORES:
        inst = Clase(snapshot, queue, intervalo_inicial=intervalo)
        inst.start()
        instancias.append((nombre, inst))
        print(f"[Main] Analizador{nombre} arrancado (PID {inst.pid}, interval={intervalo}s).")

    # ------------------------------------------------------------------
    # Esperar a que los analizadores publiquen datos (al menos un ciclo)
    # ------------------------------------------------------------------
    # El más rápido es 2s. Esperamos lo suficiente como para que todos
    # tengan al menos una iteración completa.
    espera = max(intervalo for _, _, intervalo in ANALIZADORES) + 2.0
    print(f"\n[Main] Esperando {espera:.0f} segundos para que los analizadores publiquen datos...")
    time.sleep(espera)

    # ------------------------------------------------------------------
    # Mostrar resumen del snapshot
    # ------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("[Main] Snapshot actual (resumen por vista):")
    print("=" * 60)

    for clave in snapshot:
        if clave == "timestamps":
            continue

        valor = snapshot[clave]
        if not valor:
            print(f"  {clave:20s}: <vacío>")
            continue

        # Casos especiales para mostrar algo útil
        if clave == "resumen" and isinstance(valor, dict):
            print(f"  {clave:20s}: {len(valor)} PIDs con datos")
            # Mostrar top 3 por CPU%
            top = sorted(valor.items(), key=lambda x: x[1].get("cpu_pct", 0), reverse=True)[:3]
            for pid, datos in top:
                cmd = datos.get("cmdline", "<sin cmdline>")[:30]
                print(f"      PID {pid:5d}: cpu={datos.get('cpu_pct','?')}%  [{datos.get('estado','?')}]  {cmd}")

        elif clave == "memoria" and isinstance(valor, dict):
            print(f"  {clave:20s}: {len(valor)} PIDs con datos")
            # Top 3 por RSS
            top = sorted(
                [(pid, d.get("vmrss", 0)) for pid, d in valor.items()],
                key=lambda x: x[1], reverse=True
            )[:3]
            for pid, vmrss in top:
                print(f"      PID {pid:5d}: VmRSS={vmrss} KB")

        elif clave == "sistema" and isinstance(valor, dict):
            # Sistema: un solo dict global
            cpu = valor.get("cpu", {})
            mem = valor.get("memoria", {})
            load = valor.get("load", ())
            print(f"  {clave:20s}: ---")
            if cpu and "idle_pct" in cpu:
                print(f"      CPU idle:   {cpu['idle_pct']:.1f}%")
            if mem:
                print(f"      MemTotal:   {mem.get('MemTotal')} KB")
                print(f"      MemAvailable: {mem.get('MemAvailable')} KB")
            if load:
                print(f"      Load avg:   {load[0]} / {load[1]} / {load[2]}")

        elif clave in ("threads", "fds", "senales", "scheduling"):
            print(f"  {clave:20s}: {len(valor)} PIDs con datos")

        else:
            print(f"  {clave:20s}: {len(valor) if hasattr(valor,'__len__') else '---'}")

    # ------------------------------------------------------------------
    # Shutdown limpio: detener analizadores, agregador, recolector
    # ------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("[Main] Enviando señal de fin a los procesos...")
    print("=" * 60)

    # 1. Detener analizadores
    for nombre, inst in instancias:
        print(f"[Main] Deteniendo Analizador{nombre}...")
        inst.detener()
        inst.join(timeout=5.0)       # esperar hasta 5 segundos
        if inst.is_alive():
            print(f"  ⚠️  Analizador{nombre} no terminó, forzando terminate()...")
            inst.terminate()

    # 2. Detener Agregador (None en la queue = señal de fin)
    print("[Main] Deteniendo Agregador...")
    queue.put(None)
    agregador.join(timeout=5.0)
    if agregador.is_alive():
        print("  ⚠️  Agregador no terminó, forzando terminate()...")
        agregador.terminate()

    # 3. Detener Recolector
    print("[Main] Deteniendo Recolector...")
    recolector.detener()
    recolector.join(timeout=5.0)
    if recolector.is_alive():
        print("  ⚠️  Recolector no terminó, forzando terminate()...")
        recolector.terminate()

    print("\n[Main] Todos los procesos finalizaron. Fin de la demo.")


if __name__ == "__main__":
    main()

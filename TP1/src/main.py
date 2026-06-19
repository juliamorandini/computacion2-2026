"""main.py - Punto de entrada del monitor de procesos y threads.

Orquesta la creación del estado compartido, lanza el proceso Recolector,
el Agregador y coordina el arranque de los demás componentes.
"""

from multiprocessing import Queue
import time

from estado import crear_estado
from agregador import Agregador
from recolector import Recolector


def main():
    print("Monitor de Procesos y Threads - TP1 Computación II\n")

    # ------------------------------------------------------------------
    # FASE 3: Estado compartido
    # ------------------------------------------------------------------
    snapshot, lock = crear_estado()

    # ------------------------------------------------------------------
    # FASE 4: Recolector + Agregador
    # ------------------------------------------------------------------

    # 1. Queue por donde los analizadores enviarán resultados al Agregador.
    queue = Queue()

    # 2. Instanciar y arrancar procesos.
    recolector = Recolector(snapshot, intervalo=2.0)
    agregador = Agregador(snapshot, lock, queue)

    recolector.start()
    agregador.start()

    # ------------------------------------------------------------------
    # Demo: esperar un poco para que el recolector publique PIDs y
    # luego simular que un analizador envía datos.
    # ------------------------------------------------------------------
    print("[Main] Esperando a que el Recolector publique PIDs...")
    time.sleep(2.5)

    # Mostrar los PIDs encontrados
    pids = snapshot.get("pids", [])
    print(f"[Main] Recolector encontró {len(pids)} procesos:")
    print(f"         Primeros 10 PIDs: {pids[:10]}")

    # Simular envío de datos por parte de un analizador
    print("\n[Main] Enviando datos de prueba a la queue...")
    queue.put({
        "vista": "memoria",
        "data": {"VmRSS": 1024, "VmSize": 4096}
    })

    queue.put({
        "vista": "resumen",
        "data": {"pid": 42, "estado": "R", "cpu": 5.2}
    })

    # Dar tiempo al agregador de procesar.
    time.sleep(1)

    # Verificar que llegaron al snapshot (datos + timestamps).
    print("\n[Main] Snapshot actual (vistas con datos):")
    for clave in snapshot:
        if clave == "timestamps":
            continue
        valor = snapshot[clave]
        if valor:
            print(f"  {clave}: {valor}")
        else:
            print(f"  {clave}: <vacío>")

    # ------------------------------------------------------------------
    # Shutdown limpio
    # ------------------------------------------------------------------
    print("\n[Main] Enviando señal de fin a los procesos...")
    queue.put(None)                 # Shutdown del Agregador
    recolector.detener()            # Shutdown del Recolector

    agregador.join()
    recolector.join()

    print("[Main] Todos los procesos finalizaron. Fin de la demo.")


if __name__ == "__main__":
    main()

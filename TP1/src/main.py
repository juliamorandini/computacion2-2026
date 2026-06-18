"""main.py - Punto de entrada del monitor de procesos y threads.

Orquesta la creación del estado compartido, lanza el proceso Agregador
y coordina el arranque de los demás componentes.
"""

from multiprocessing import Queue
import time

from estado import crear_estado
from agregador import Agregador


def main():
    print("Monitor de Procesos y Threads - TP1 Computación II\n")

    # ------------------------------------------------------------------
    # FASE 3: Estado compartido y Agregador
    # ------------------------------------------------------------------

    # 1. Crear el estado compartido (snapshot + lock).
    snapshot, lock = crear_estado()

    # 2. Crear la Queue única por donde los analizadores enviarán datos
    #    al Agregador.
    queue = Queue()

    # 3. Instanciar y arrancar el Agregador.
    agregador = Agregador(snapshot, lock, queue)
    agregador.start()

    # ------------------------------------------------------------------
    # Ejemplo mínimo: simular un analizador enviando datos.
    # En la práctica real serán 7 procesos analizadores independientes.
    # ------------------------------------------------------------------
    print("[Main] Enviando datos de prueba a la queue...")

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

    # Verificar que llegaron al snapshot.
    print("\n[Main] Snapshot actual:")
    for clave in snapshot:
        if clave == "timestamps":
            continue
        print(f"  {clave}: {snapshot[clave]}")

    # ------------------------------------------------------------------
    # Shutdown limpio
    # ------------------------------------------------------------------
    print("\n[Main] Enviando señal de fin al Agregador...")
    queue.put(None)   # Señal de shutdown.
    agregador.join()

    print("[Main] Agregador terminado. Fin de la demo.")


if __name__ == "__main__":
    main()

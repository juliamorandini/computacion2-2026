#!/usr/bin/env python3
"""Monitores en segundo plano usando Daemon Threads."""
import threading
import time
import random

def monitor_metrica(nombre, intervalo):
    """Reporta métricas infinitamente."""
    while True:
        uso = random.uniform(10.0, 95.0)
        print(f"[Monitor {nombre}] Uso actual: {uso:.1f}%")
        time.sleep(intervalo)

if __name__ == "__main__":
    print("Iniciando sistema principal...")

    # Creamos y lanzamos los daemons
    metricas = [("CPU", 1.5), ("Memoria RAM", 2.0), ("Disco I/O", 3.0)]
    
    for nombre, intervalo in metricas:
        t = threading.Thread(target=monitor_metrica, args=(nombre, intervalo))
        t.daemon = True  # ¡CLAVE! Se marcan como daemon ANTES del start
        t.start()

    print("Main trabajando por 10 segundos...")
    for i in range(10, 0, -1):
        print(f"Main termina en {i}...")
        time.sleep(1)

    print("Main finalizado. Los daemons morirán instantáneamente ahora.")
    # Al terminar el main, no hay .join() para los daemons, mueren solos.
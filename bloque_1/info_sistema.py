#!/usr/bin/env python3
"""Script de información del sistema para el Ejercicio de Síntesis."""

import sys
import platform
import os

def main():
    print("=" * 50)
    print("📊 INFORMACIÓN DEL SISTEMA")
    print("=" * 50)

    # 1. Versión de Python
    print(f"Versión de Python: {sys.version.split()[0]}")

    # 2. Sistema operativo (nombre, versión)
    print(f"Sistema Operativo: {platform.system()} {platform.release()}")
    if hasattr(os, 'uname'):
        print(f"Hostname (Nodo): {os.uname().nodename}")

    # 3. Cantidad de CPUs disponibles
    cpus = os.cpu_count()
    print(f"CPUs disponibles: {cpus}")

    # 4. Memoria disponible (Lectura directa en Linux/Docker)
    try:
        with open('/proc/meminfo', 'r') as f:
            mem_total_kb = int(next(f).split()[1])
            print(f"Memoria Total: {mem_total_kb // 1024} MB")
    except FileNotFoundError:
        print("Memoria Total: No disponible sin librerías externas en este SO.")

    # 5. Variables de entorno que empiecen con "PYTHON"
    print("-" * 50)
    print("Variables de entorno 'PYTHON*':")
    python_envs = {k: v for k, v in os.environ.items() if k.startswith("PYTHON")}
    
    if python_envs:
        for k, v in python_envs.items():
            print(f"  {k} = {v}")
    else:
        print("  (Ninguna variable de entorno encontrada)")
    
    print("=" * 50)

if __name__ == "__main__":
    main()
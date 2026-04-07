#!/usr/bin/env python3
"""Versión con subprocess para comparar."""
import subprocess
import sys
import time

def main():
    if len(sys.argv) < 2:
        print(f"Uso: {sys.argv[0]} comando1 [comando2 ...]")
        sys.exit(1)

    comandos = sys.argv[1:]
    inicio = time.time()

    # 1. Iniciar todos los procesos
    # Popen inicia el proceso en segundo plano y SIGUE ADELANTE inmediatamente
    procesos = []
    for cmd in comandos:
        # shell=True permite pasar el comando como un string (ej: "sleep 2")
        proc = subprocess.Popen(cmd, shell=True)
        print(f"[{proc.pid}] Iniciado con subprocess: {cmd}")
        procesos.append((proc, cmd))

    # 2. Esperar a que todos terminen
    resultados = []
    for proc, cmd in procesos:
        codigo = proc.wait() # Aquí el padre se detiene hasta que este proceso termine
        print(f"[{proc.pid}] Terminado: {cmd} (código: {codigo})")
        resultados.append(codigo)

    duracion = time.time() - inicio

    exitosos = sum(1 for c in resultados if c == 0)
    print(f"\nResumen (Versión Subprocess):")
    print(f"- Comandos ejecutados: {len(comandos)}")
    print(f"- Exitosos: {exitosos}")
    print(f"- Fallidos: {len(comandos) - exitosos}")
    print(f"- Tiempo total: {duracion:.2f}s")

if __name__ == "__main__":
    main()
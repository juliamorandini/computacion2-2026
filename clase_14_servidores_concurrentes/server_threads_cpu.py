#!/usr/bin/env python3
"""Servidor eco: un thread por cliente, con trabajo CPU real.

Este archivo es para el Ejercicio 6 de la Clase 14: demuestra que
los threads con GIL NO escalan cuando el trabajo es CPU-bound.
Comparalo con server_fork_cpu.py para ver la diferencia.

Uso:
    python3 server_threads_cpu.py [puerto] [--cpu N]

    --cpu N: iteraciones del cálculo (default 2_000_000)
"""
import socket
import sys
import threading

HOST = '0.0.0.0'
PUERTO = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 8080
CPU_N = int(sys.argv[sys.argv.index('--cpu') + 1]) if '--cpu' in sys.argv else 2_000_000

# Estado compartido entre threads: necesita lock (clase 11).
clientes_activos = 0
pico_simultaneos = 0
lock = threading.Lock()


def trabajo_cpu(n):
    """CPU-bound de verdad: NO libera el GIL.

    Mientras este loop corre, ningún otro thread ejecuta bytecode
    Python. Los threads no escalan en paralelo para esto.
    """
    total = 0
    for i in range(n):
        total += i * i
    return total


def atender(conn, direccion):
    """Corre en su propio thread, uno por cliente."""
    global clientes_activos, pico_simultaneos
    with lock:
        clientes_activos += 1
        pico_simultaneos = max(pico_simultaneos, clientes_activos)
    try:
        trabajo_cpu(CPU_N)              # <-- el trabajo pesado
        with conn:
            while True:
                datos = conn.recv(4096)
                if not datos:
                    break
                conn.sendall(datos)
    except (ConnectionResetError, BrokenPipeError):
        pass
    finally:
        with lock:
            clientes_activos -= 1


def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as servidor:
        servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        servidor.bind((HOST, PUERTO))
        servidor.listen(128)
        print(f'[threads-cpu] escuchando en {HOST}:{PUERTO} '
              f'(CPU: {CPU_N} iteraciones por cliente)')

        while True:
            conn, direccion = servidor.accept()
            hilo = threading.Thread(target=atender, args=(conn, direccion),
                                    daemon=True)
            hilo.start()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print(f'\nServidor detenido. Pico de clientes simultáneos: {pico_simultaneos}')
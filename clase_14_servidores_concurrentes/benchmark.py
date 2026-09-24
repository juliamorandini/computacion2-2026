#!/usr/bin/env python3
"""Benchmark de servidores eco (Clase 14).

Lanza N clientes concurrentes. Cada uno abre una conexión, manda un
mensaje, espera el eco y cierra. Reporta cuántos completaron, el tiempo
total y las latencias (mín, máx, mediana).

Detecta heurísticamente la "atención en serie": si la latencia máxima
es mucho mayor que la mínima, avisa.

Uso:
    python3 benchmark.py --clientes 20
    python3 benchmark.py --clientes 20 --puerto 8080 --host localhost
    python3 benchmark.py --clientes 50 --mensaje hola --timeout 120
"""
import argparse
import socket
import statistics
import threading
import time


def un_cliente(host, puerto, mensaje, timeout, iniciar, resultados, idx):
    """Un cliente: conecta, manda, lee el eco, cierra."""
    iniciar.wait()                       # arranque simultáneo
    t0 = time.perf_counter()
    try:
        with socket.create_connection((host, puerto), timeout=timeout) as s:
            s.settimeout(timeout)
            s.sendall(mensaje)
            recibido = b''
            while len(recibido) < len(mensaje):
                chunk = s.recv(4096)
                if not chunk:
                    break
                recibido += chunk
        t1 = time.perf_counter()
        ok = (recibido == mensaje)
        resultados[idx] = (t1 - t0, ok, None if ok else f'eco distinto: {recibido!r}')
    except Exception as e:
        t1 = time.perf_counter()
        resultados[idx] = (t1 - t0, False, repr(e))


def main():
    p = argparse.ArgumentParser(description='Benchmark de servidores eco')
    p.add_argument('--host', default='localhost')
    p.add_argument('--puerto', type=int, default=8080)
    p.add_argument('--clientes', type=int, default=20)
    p.add_argument('--mensaje', default='hola')
    p.add_argument('--timeout', type=float, default=120.0)
    args = p.parse_args()

    mensaje = args.mensaje.encode('utf-8')
    resultados = [None] * args.clientes
    iniciar = threading.Event()
    hilos = []

    for i in range(args.clientes):
        h = threading.Thread(
            target=un_cliente,
            args=(args.host, args.puerto, mensaje, args.timeout,
                  iniciar, resultados, i),
            daemon=True)
        hilos.append(h)
        h.start()

    t0 = time.perf_counter()
    iniciar.set()                        # ¡arrancan todos juntos!
    for h in hilos:
        h.join()
    t_total = time.perf_counter() - t0

    exitos = sum(1 for r in resultados if r and r[1])
    fallos = args.clientes - exitos
    latencias = [r[0] for r in resultados if r and r[1]]

    print()
    print(f'Clientes: {args.clientes}   Exitosos: {exitos}   Fallos: {fallos}')
    print(f'Tiempo total: {t_total:.2f} s')
    if latencias:
        lmin = min(latencias)
        lmax = max(latencias)
        lmed = statistics.median(latencias)
        print(f'Latencia mínima:  {lmin:.3f} s')
        print(f'Latencia máxima:  {lmax:.3f} s')
        print(f'Latencia mediana: {lmed:.3f} s')
        print(f'Throughput:       {exitos / t_total:.1f} clientes/s')

        # Detección heurística de atención en serie:
        # si la latencia máxima es > 10× la mínima, algo raro pasa.
        if lmin > 0.01 and lmax > 10 * lmin:
            print()
            print(f'Nota: latencia máxima ≈ {lmax/lmin:.0f}× la mínima — '
                  f'posible atención en serie.')

    if fallos:
        print()
        print('Primeros fallos:')
        for r in resultados:
            if r and not r[1]:
                print(f'  - {r[2]}')
                break


if __name__ == '__main__':
    main()
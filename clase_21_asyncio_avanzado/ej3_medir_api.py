#!/usr/bin/env python3
"""Clase 21 - Ejercicio 3, parte D: mide cuanto tarda GET /tareas mientras
POST /hashear esta calculando, sin executor y con executor.

Levanta uvicorn como subproceso con ej3_api_hashear.py en cada modo.

Uso:
    python3 ej3_medir_api.py
"""
import os
import subprocess
import sys
import threading
import time

import httpx

PUERTO = 8001


def medir(modo):
    env = dict(os.environ, MODO=modo)
    srv = subprocess.Popen(
        [sys.executable, '-m', 'uvicorn', 'ej3_api_hashear:app',
         '--port', str(PUERTO), '--log-level', 'warning'],
        env=env, cwd=os.path.dirname(os.path.abspath(__file__)))
    base = f'http://127.0.0.1:{PUERTO}'
    try:
        for _ in range(50):                      # esperar a que levante
            try:
                httpx.get(base + '/tareas', timeout=0.5)
                break
            except httpx.HTTPError:
                time.sleep(0.2)

        lat = {}

        def pesado():
            t0 = time.perf_counter()
            httpx.post(base + '/hashear', timeout=60)
            lat['pesado'] = time.perf_counter() - t0

        hilo = threading.Thread(target=pesado)
        hilo.start()
        time.sleep(0.5)                          # que el calculo ya este corriendo
        t0 = time.perf_counter()
        httpx.get(base + '/tareas', timeout=60)
        lat['get'] = time.perf_counter() - t0
        hilo.join()
        return lat
    finally:
        srv.terminate()
        srv.wait()


if __name__ == '__main__':
    for modo in ('bloqueante', 'executor'):
        r = medir(modo)
        print(f'  {modo:<11} POST /hashear: {r["pesado"]:5.2f}s   '
              f'GET /tareas durante el calculo: {r["get"] * 1000:8.1f} ms')


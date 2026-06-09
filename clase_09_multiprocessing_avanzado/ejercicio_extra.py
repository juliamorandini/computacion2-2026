#!/usr/bin/env python3
"""Estimación de Pi usando Monte Carlo paralelizado."""
from multiprocessing import Pool
import random

def lanzar_dardos(n):
    dentro_circulo = 0
    for _ in range(n):
        x = random.uniform(0, 1)
        y = random.uniform(0, 1)
        if x**2 + y**2 <= 1:
            dentro_circulo += 1
    return dentro_circulo

if __name__ == "__main__":
    DARDOS_TOTALES = 10_000_000
    WORKERS = 4
    dardos_por_worker = DARDOS_TOTALES // WORKERS

    with Pool(WORKERS) as pool:
        resultados = pool.map(lanzar_dardos, [dardos_por_worker] * WORKERS)
    
    total_dentro = sum(resultados)
    pi_estimado = 4 * total_dentro / DARDOS_TOTALES
    
    print(f"Pi estimado: {pi_estimado}")
#!/usr/bin/env python3
"""Memoria compartida con Value y Array."""
from multiprocessing import Process, Value, Array
import time

def incrementar(contador, n_veces, id):
    for _ in range(n_veces):
        with contador.get_lock():
            contador.value += 1
    print(f"Worker {id} terminó sus {n_veces} incrementos")

def llenar_array(arr, valor_inicial, id):
    inicio = id * (len(arr) // 4)
    fin = inicio + (len(arr) // 4)
    for i in range(inicio, fin):
        arr[i] = valor_inicial + i

if __name__ == "__main__":
    contador = Value('i', 0)
    procs = [Process(target=incrementar, args=(contador, 10000, i)) for i in range(4)]
    
    for p in procs: p.start()
    for p in procs: p.join()

    print(f"\nContador final: {contador.value}")
    assert contador.value == 40000, "¡Race condition! Falta el lock"

    arr = Array('i', 100)
    procs = [Process(target=llenar_array, args=(arr, 1000, i)) for i in range(4)]
    
    for p in procs: p.start()
    for p in procs: p.join()

    print(f"Array (primeros 10): {list(arr)[:10]}")
    print(f"Array (últimos 10): {list(arr)[-10:]}")
    
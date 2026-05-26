#!/usr/bin/env python3
"""Pipeline de 3 etapas con multiprocessing."""
from multiprocessing import Process, Queue
import time

def etapa_multiplicar(input_q, output_q):
    while True:
        item = input_q.get()
        if item is None:
            output_q.put(None)
            break
        time.sleep(0.05)
        output_q.put(item * 2)

def etapa_sumar(input_q, output_q):
    while True:
        item = input_q.get()
        if item is None:
            output_q.put(None)
            break
        time.sleep(0.05)
        output_q.put(item + 10)

def etapa_formatear(input_q, output_q):
    while True:
        item = input_q.get()
        if item is None:
            output_q.put(None)
            break
        time.sleep(0.05)
        output_q.put(f"resultado_{item:03d}")

if __name__ == "__main__":
    q1, q2, q3, q4 = Queue(), Queue(), Queue(), Queue()

    p1 = Process(target=etapa_multiplicar, args=(q1, q2))
    p2 = Process(target=etapa_sumar, args=(q2, q3))
    p3 = Process(target=etapa_formatear, args=(q3, q4))

    p1.start(); p2.start(); p3.start()

    # Alimentar el pipeline
    for i in range(10):
        q1.put(i)
    q1.put(None)

    # Recoger resultados
    while True:
        result = q4.get()
        if result is None:
            break
        print(f"Final: {result}")

    p1.join(); p2.join(); p3.join()
import multiprocessing
import time
import random

def worker(n):
    espera = random.uniform(0.5, 2)
    time.sleep(espera)
    print(f"Worker {n} terminó después de {espera:.2f}s")

if __name__ == "__main__":
    inicio = time.time()
    procesos = []

    for i in range(5):
        p = multiprocessing.Process(target=worker, args=(i,))
        procesos.append(p)
        p.start()

    for p in procesos:
        p.join()

    tiempo_total = time.time() - inicio
    print(f"\nTodos los procesos terminaron.")
    print(f"Tiempo total del programa: {tiempo_total:.2f} segundos")
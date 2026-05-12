import multiprocessing
import time

def productor(cola):
    for i in range(1, 11):
        item = f"Dato-{i}"
        cola.put(item)
        print(f"[Productor] Generado: {item}")
        time.sleep(0.2)
    cola.put(None)  # Señal de fin (Sentinel)

def consumidor(cola):
    while True:
        item = cola.get()
        if item is None:
            break
        print(f"[Consumidor] Procesado: {item}")

if __name__ == "__main__":
    q = multiprocessing.Queue()
    p1 = multiprocessing.Process(target=productor, args=(q,))
    p2 = multiprocessing.Process(target=consumidor, args=(q,))

    p1.start()
    p2.start()
    p1.join()
    p2.join()
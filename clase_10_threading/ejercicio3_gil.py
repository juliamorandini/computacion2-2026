#!/usr/bin/env python3
import threading
import time
import math

def tarea_cpu(n):
    return sum(math.sqrt(i) for i in range(n))

def ejecutar_con_hilos(n, cantidad_hilos):
    hilos = []
    carga_por_hilo = n // cantidad_hilos
    
    inicio = time.time()
    for _ in range(cantidad_hilos):
        h = threading.Thread(target=tarea_cpu, args=(carga_por_hilo,))
        h.start()
        hilos.append(h)
        
    for h in hilos:
        h.join()
    return time.time() - inicio

if __name__ == "__main__":
    N = 10_000_000
    
    # Secuencial (1 hilo)
    inicio = time.time()
    tarea_cpu(N)
    t_seq = time.time() - inicio
    print(f"Secuencial (1 hilo): {t_seq:.2f}s")
    
    # 2 hilos
    t_2 = ejecutar_con_hilos(N, 2)
    print(f"Con 2 hilos:         {t_2:.2f}s")
    
    # 4 hilos
    t_4 = ejecutar_con_hilos(N, 4)
    print(f"Con 4 hilos:         {t_4:.2f}s")
    
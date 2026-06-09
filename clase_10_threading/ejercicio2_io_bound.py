#!/usr/bin/env python3
import threading
import time

def simular_descarga(url, demora):
    time.sleep(demora)

if __name__ == "__main__":
    urls = [f"http://sitio.com/archivo_{i}.zip" for i in range(5)]
    demora = 1.0
    
    # 1. Ejecución secuencial
    inicio = time.time()
    for url in urls:
        simular_descarga(url, demora)
    t_seq = time.time() - inicio
    print(f"Tiempo Secuencial: {t_seq:.2f}s")
    
    # 2. Ejecución paralela con hilos
    inicio = time.time()
    hilos = []
    for url in urls:
        h = threading.Thread(target=simular_descarga, args=(url, demora))
        h.start()
        hilos.append(h)
        
    for h in hilos:
        h.join()
    t_par = time.time() - inicio
    print(f"Tiempo Paralelo: {t_par:.2f}s")
    
    print(f"Factor de mejora: {t_seq / t_par:.2f}x")
#!/usr/bin/env python3
import threading
import queue
import time

def procesar_imagen(q, worker_id, estadisticas, lock):
    procesadas = 0
    while True:
        imagen = q.get()
        if imagen is None:  # Señal de fin
            q.task_done()
            break
            
        # Simular procesamiento
        time.sleep(0.5)
        procesadas += 1
        q.task_done()
        
    with lock:
        estadisticas[worker_id] = procesadas

if __name__ == "__main__":
    q = queue.Queue()
    estadisticas = {}
    lock = threading.Lock()
    
    # 1. Iniciar workers
    hilos = []
    for i in range(4):
        h = threading.Thread(target=procesar_imagen, args=(q, f"Worker-{i+1}", estadisticas, lock))
        h.start()
        hilos.append(h)
        
    # 2. Agregar trabajo (imágenes)
    inicio = time.time()
    for i in range(1, 21):
        q.put(f"imagen_{i:03d}.jpg")
        
    # 3. Esperar a que la cola se vacíe de tareas útiles
    q.join()
    
    # 4. Enviar señales de apagado
    for _ in range(4):
        q.put(None)
        
    for h in hilos:
        h.join()
        
    # Resultados
    t_total = time.time() - inicio
    for worker, procesadas in estadisticas.items():
        print(f"{worker} procesó {procesadas} imágenes")
    print(f"Tiempo total: {t_total:.2f}s")
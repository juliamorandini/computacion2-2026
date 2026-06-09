#!/usr/bin/env python3
import threading
import time

def imprimir_numeros():
    nombre = threading.current_thread().name
    for i in range(1, 6):
        print(f"[{nombre}] Número: {i}")
        time.sleep(0.2)

if __name__ == "__main__":
    print("Iniciando programa principal...")
    hilos = []
    
    # Crear y lanzar 3 hilos
    for i in range(3):
        h = threading.Thread(target=imprimir_numeros, name=f"Hilo-{i+1}")
        h.start()
        hilos.append(h)
        
    # Esperar a que todos terminen
    for h in hilos:
        h.join()
        
    print("Listo")
#!/usr/bin/env python3
import threading
import time
import sys

def tarea_infinita():
    while True:
        print("trabajando...")
        time.sleep(1)

if __name__ == "__main__":
    # Si pasás cualquier argumento al script, lo hace daemon
    usar_daemon = len(sys.argv) > 1 
    
    hilo = threading.Thread(target=tarea_infinita)
    hilo.daemon = usar_daemon
    hilo.start()
    
    print(f"Main iniciado. Daemon = {usar_daemon}")
    time.sleep(3)
    print("Main terminando...")
    # Si daemon=False, el script se quedará colgado acá para siempre.
    # Si daemon=True, el script terminará ahora mismo.
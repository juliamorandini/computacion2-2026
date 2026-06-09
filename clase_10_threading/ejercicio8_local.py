#!/usr/bin/env python3
import threading
import time
import random

contexto_hilo = threading.local()

def get_contexto():
    return f"Usuario: {contexto_hilo.usuario} | IP: {contexto_hilo.ip} | Time: {contexto_hilo.timestamp:.2f}"

def atender_request(usuario, ip):
    # Guardamos los datos en el espacio local del hilo
    contexto_hilo.usuario = usuario
    contexto_hilo.ip = ip
    contexto_hilo.timestamp = time.time()
    
    # Simulamos algo de procesamiento
    time.sleep(random.uniform(0.1, 0.5))
    
    # Leemos la variable global (pero obtenemos los datos específicos de ESTE hilo)
    nombre_hilo = threading.current_thread().name
    print(f"[{nombre_hilo}] Procesando -> {get_contexto()}")

if __name__ == "__main__":
    requests = [
        ("juan_perez", "192.168.1.10"),
        ("maria_gomez", "10.0.0.5"),
        ("admin", "127.0.0.1"),
        ("invitado", "172.16.0.4")
    ]
    
    hilos = []
    for i, (usr, ip) in enumerate(requests):
        h = threading.Thread(target=atender_request, args=(usr, ip), name=f"Req-{i+1}")
        h.start()
        hilos.append(h)
        
    for h in hilos:
        h.join()
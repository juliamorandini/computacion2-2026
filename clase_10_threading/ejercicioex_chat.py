#!/usr/bin/env python3
"""Chat multi-hilo usando Queue para comunicación segura."""
import threading
import queue
import time
import random

def usuario_emisor(nombre, canal_q):
    """Simula un usuario escribiendo mensajes."""
    for i in range(4):
        # Tiempo aleatorio pensando qué escribir
        time.sleep(random.uniform(0.1, 0.8))
        mensaje = f"Hola, soy el mensaje {i+1} de {nombre}"
        canal_q.put(f"[{nombre}] {mensaje}")
    print(f"--- {nombre} se desconectó ---")

def display_receptor(canal_q):
    """Único hilo encargado de imprimir en pantalla para no mezclar prints."""
    while True:
        mensaje = canal_q.get()
        if mensaje is None:  # Señal de apagado
            break
        print(f"📺 PANTALLA: {mensaje}")
        canal_q.task_done()

if __name__ == "__main__":
    chat_q = queue.Queue()

    # Iniciamos el hilo que muestra los mensajes
    hilo_pantalla = threading.Thread(target=display_receptor, args=(chat_q,))
    hilo_pantalla.start()

    # Iniciamos varios usuarios
    usuarios = ["Alice", "Bob", "Charlie"]
    hilos_usuarios = []
    for u in usuarios:
        t = threading.Thread(target=usuario_emisor, args=(u, chat_q))
        t.start()
        hilos_usuarios.append(t)

    # Esperamos a que todos terminen de escribir
    for t in hilos_usuarios:
        t.join()

    # Apagamos la pantalla
    chat_q.put(None)
    hilo_pantalla.join()
    print("Servidor de chat cerrado.")
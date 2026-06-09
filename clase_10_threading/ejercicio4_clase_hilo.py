#!/usr/bin/env python3
import threading
import time

class ContadorHilo(threading.Thread):
    def __init__(self, nombre, limite):
        super().__init__()
        self.nombre = nombre
        self.limite = limite
        self.resultado = ""

    def run(self):
        numeros = []
        for i in range(1, self.limite + 1):
            numeros.append(str(i))
            time.sleep(0.1)
        self.resultado = ",".join(numeros)

if __name__ == "__main__":
    hilos = [
        ContadorHilo("Hilo-A", 3),
        ContadorHilo("Hilo-B", 5),
        ContadorHilo("Hilo-C", 4)
    ]
    
    for h in hilos:
        h.start()
        
    for h in hilos:
        h.join()
        print(f"Resultado de {h.nombre}: {h.resultado}")
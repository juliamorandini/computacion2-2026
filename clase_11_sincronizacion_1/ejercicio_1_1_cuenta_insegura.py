#!/usr/bin/env python3
"""Demostración de race condition en cuenta bancaria."""
import threading
import time
import random

class CuentaInsegura:
    def __init__(self, saldo):
        self.saldo = saldo

    def depositar(self, cantidad):
        actual = self.saldo
        time.sleep(0.001)  # Simula procesamiento
        self.saldo = actual + cantidad

    def retirar(self, cantidad):
        actual = self.saldo
        time.sleep(0.001)
        if actual >= cantidad:
            self.saldo = actual - cantidad
            return True
        return False

# Probar
cuenta = CuentaInsegura(1000)

def operaciones_aleatorias():
    for _ in range(100):
        if random.choice([True, False]):
            cuenta.depositar(10)
        else:
            cuenta.retirar(10)

threads = [threading.Thread(target=operaciones_aleatorias) for _ in range(10)]
for t in threads:
    t.start()
for t in threads:
    t.join()

print(f"Saldo esperado: 1000 (si no hay errores)")
print(f"Saldo obtenido: {cuenta.saldo}")
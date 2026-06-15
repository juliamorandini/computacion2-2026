#!/usr/bin/env python3
"""Cuenta bancaria thread-safe."""
import threading
import time
import random

class CuentaSegura:
    def __init__(self, saldo):
        self.saldo = saldo
        self.lock = threading.Lock()

    def depositar(self, cantidad):
        with self.lock:
            actual = self.saldo
            time.sleep(0.001)
            self.saldo = actual + cantidad

    def retirar(self, cantidad):
        with self.lock:
            actual = self.saldo
            time.sleep(0.001)
            if actual >= cantidad:
                self.saldo = actual - cantidad
                return True
            return False


cuenta = CuentaSegura(1000)

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
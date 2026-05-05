#!/usr/bin/env python3
"""
Banco con cuentas en memoria compartida.
Múltiples procesos realizan transferencias.

NOTA: Este ejercicio intencionalmente NO usa sincronización
para que puedas observar las race conditions.
"""
from multiprocessing import Process, Array, Value
import random
import time

NUM_CUENTAS = 5
SALDO_INICIAL = 1000
NUM_PROCESOS = 3
TRANSFERENCIAS_POR_PROCESO = 100

def mostrar_saldos(cuentas, etiqueta):
    """Muestra los saldos de todas las cuentas."""
    saldos = [cuentas[i] for i in range(NUM_CUENTAS)]
    total = sum(saldos)
    print(f"[{etiqueta}] Saldos: {saldos} | Total: {total}")

def cajero(cuentas, cajero_id, num_transferencias):
    """Un cajero que realiza transferencias entre cuentas."""
    for _ in range(num_transferencias):
        # Elegir dos cuentas diferentes al azar
        origen = random.randint(0, NUM_CUENTAS - 1)
        destino = random.randint(0, NUM_CUENTAS - 1)
        while destino == origen:
            destino = random.randint(0, NUM_CUENTAS - 1)

        # Transferir un monto aleatorio
        monto = random.randint(1, 50)

        if cuentas[origen] >= monto:
            # Estas dos operaciones NO son atómicas
            cuentas[origen] -= monto
            cuentas[destino] += monto

    print(f"[Cajero {cajero_id}] Completó {num_transferencias} transferencias")

# Crear array compartido con saldos iniciales
cuentas = Array('i', [SALDO_INICIAL] * NUM_CUENTAS)

print(f"=== Banco con {NUM_CUENTAS} cuentas ===")
print(f"=== Saldo total esperado: {NUM_CUENTAS * SALDO_INICIAL} ===\n")

mostrar_saldos(cuentas, "INICIO")

# Lanzar cajeros
procesos = []
for i in range(NUM_PROCESOS):
    p = Process(target=cajero, args=(cuentas, i, TRANSFERENCIAS_POR_PROCESO))
    p.start()
    procesos.append(p)

for p in procesos:
    p.join()

mostrar_saldos(cuentas, "FINAL")

# Verificar integridad
total_final = sum(cuentas[i] for i in range(NUM_CUENTAS))
total_esperado = NUM_CUENTAS * SALDO_INICIAL

if total_final != total_esperado:
    print(f"\n¡ERROR! Se perdieron ${total_esperado - total_final}")
    print("Esto es una race condition - se necesita sincronización")
else:
    print(f"\nTodo correcto (pero fue suerte - ejecutalo varias veces)")
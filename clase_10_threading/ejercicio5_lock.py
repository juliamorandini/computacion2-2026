#!/usr/bin/env python3
import threading
import time

saldo = 1000
lock = threading.Lock()

def retirar_inseguro(monto):
    """Genera números negativos porque se pisan entre hilos."""
    global saldo
    if saldo >= monto:
        time.sleep(0.001) 
        saldo -= monto
        print(f"Retiro de ${monto} exitoso. Saldo: ${saldo}")
    else:
        print(f"Saldo insuficiente para retirar ${monto}")

def retirar_seguro(monto):
    """Versión corregida usando Lock."""
    global saldo
    with lock:  # Solo 1 hilo entra a este bloque a la vez
        if saldo >= monto:
            time.sleep(0.001) 
            saldo -= monto
            print(f"Retiro de ${monto} exitoso. Saldo: ${saldo}")
        else:
            print(f"Saldo insuficiente para retirar ${monto}")

if __name__ == "__main__":
    print("=== PRUEBA SEGURA (CON LOCK) ===")
    saldo = 1000
    hilos = [threading.Thread(target=retirar_seguro, args=(200,)) for _ in range(10)]
    
    for h in hilos: h.start()
    for h in hilos: h.join()
    
    print(f"\nSaldo final esperado: $0. Obtenido: ${saldo}")
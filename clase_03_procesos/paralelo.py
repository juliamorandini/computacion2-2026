#!/usr/bin/env python3
import os
import sys
import time

def main():
    # Validar que recibimos comandos
    if len(sys.argv) < 2:
        print(f"Uso: {sys.argv[0]} \"comando1\" \"comando2\" ...")
        sys.exit(1)

    comandos = sys.argv[1:]
    inicio = time.time()
    
    # Diccionario para guardar {PID: nombre_del_comando}
    hijos_activos = {}

    # --- PASO 1: LANZAR TODOS LOS PROCESOS ---
    # Los lanzamos "al ruedo" todos juntos
    for cmd_texto in comandos:
        pid = os.fork()
        
        if pid == 0:
            # Proceso HIJO
            partes = cmd_texto.split()
            try:
                # El hijo se transforma en el comando
                os.execvp(partes[0], partes)
            except OSError:
                print(f"Error: No se pudo ejecutar '{partes[0]}'")
                os._exit(1)
        else:
            # Proceso PADRE
            hijos_activos[pid] = cmd_texto
            print(f"[{pid}] Iniciado: {cmd_texto}")

    # --- PASO 2: ESPERAR A QUE TODOS TERMINEN ---
    exitosos = 0
    fallidos = 0

    print(f"\nPadre: esperando a {len(hijos_activos)} comandos...\n")

    while hijos_activos:
        # wait() captura al PRIMER hijo que termine
        pid_terminado, status = os.wait()
        
        # Recuperamos el nombre del comando usando el PID
        cmd_nombre = hijos_activos.pop(pid_terminado)
        codigo = os.WEXITSTATUS(status)
        
        if codigo == 0:
            exitosos += 1
        else:
            fallidos += 1
            
        print(f"[{pid_terminado}] Terminado: {cmd_nombre} (código: {codigo})")

    # --- PASO 3: RESUMEN Y TIEMPO ---
    fin = time.time()
    duracion = fin - inicio


if __name__ == "__main__":
    main()
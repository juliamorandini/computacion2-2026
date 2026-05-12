import multiprocessing
import os
import subprocess

def tarea_hijo():
    print(f"PID hijo {os.getpid()}")
    # Usamos subprocess para ejecutar el comando, similar a execl
    subprocess.run(["ls", "-l", "/home"])

if __name__ == "__main__":
    print(f"PID padre {os.getpid()}")
    
    # Creamos el proceso
    p = multiprocessing.Process(target=tarea_hijo)
    
    # Lo lanzamos (reemplaza el fork manual)
    p.start()
    
    # Esperamos a que termine (reemplaza el waitpid manual)
    p.join()

    print(f"Terminó el código {os.getpid()}")

"""Con multiprocessing te ahorrás la estructura condicional if pid == 0 porque separas el hijo en una fucnion"""


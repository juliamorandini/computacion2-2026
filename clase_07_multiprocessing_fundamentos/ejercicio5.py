import multiprocessing
import time

def tarea_rapida():
    pass

def test_metodo(metodo):
    # Intentamos forzar el método (puede fallar si ya se usó en el script)
    try:
        multiprocessing.set_start_method(metodo, force=True)
    except RuntimeError:
        pass
    
    inicio = time.time()
    procesos = []
    for _ in range(100):
        p = multiprocessing.Process(target=tarea_rapida)
        p.start()
        procesos.append(p)
    
    for p in procesos:
        p.join()
    
    return time.time() - inicio

if __name__ == "__main__":
    # El método 'fork' es nativo en Linux, 'spawn' es el default en Windows/macOS
    t_fork = test_metodo('fork')
    print(f"Tiempo con 'fork':  {t_fork:.4f}s")
    
    t_spawn = test_metodo('spawn')
    print(f"Tiempo con 'spawn': {t_spawn:.4f}s")
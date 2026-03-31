import time
from contextlib import contextmanager

# Implementación A: Clase con __enter__ y __exit__
class Timer:
    def __init__(self, name=None):
        self.name = name
        self.start_time = None
        self.end_time = None

    @property
    def elapsed(self):
        if self.start_time is None:
            return 0.0
        # Si ya terminó, usa end_time; si no, el tiempo actual
        actual = self.end_time if self.end_time else time.perf_counter()
        return actual - self.start_time

    def __enter__(self):
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.perf_counter()
        if self.name:
            print(f"[Timer] {self.name}: {self.elapsed:.3f}s")

# Implementación B: Usando @contextmanager
@contextmanager
def timer_func(name=None):
    class TimeInfo:
        def __init__(self):
            self.start = time.perf_counter()
        @property
        def elapsed(self):
            return time.perf_counter() - self.start
            
    t = TimeInfo()
    try:
        yield t
    finally:
        if name:
            print(f"[Timer] {name}: {t.elapsed:.3f}s")

# --- Bloque de prueba (opcional) ---
if __name__ == "__main__":
    with Timer("Procesamiento de datos"):
        datos = [x**2 for x in range(1000000)]

    with Timer() as t:
        time.sleep(0.5)
        print(f"El bloque tardó {t.elapsed:.3f} segundos")
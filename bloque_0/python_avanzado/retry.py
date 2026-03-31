import time
import random
import functools

def retry(max_attempts=3, delay=1, exceptions=(Exception,)):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts:
                        print(f"Intento {attempt}/{max_attempts} falló: {e}. Esperando {delay}s...")
                        time.sleep(delay)
                    else:
                        print(f"Intento {attempt}/{max_attempts} falló.")
            
            raise last_exception
        return wrapper
    return decorator

# --- Bloque de prueba (opcional) ---
if __name__ == "__main__":
    @retry(max_attempts=3, delay=1, exceptions=(ConnectionError,))
    def conectar_servidor():
        if random.random() < 0.7:
            raise ConnectionError("Servidor no disponible")
        return "Conectado exitosamente"

    try:
        print(conectar_servidor())
    except ConnectionError:
        print("Falló después de todos los intentos.")
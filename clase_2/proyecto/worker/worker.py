import redis
import time
import os

# Usamos el nombre del servicio 'redis' definido en docker-compose
r = redis.Redis(host='redis', port=6379, decode_responses=True)

print("Worker iniciado. Incrementando contador...")
while True:
    nuevo_valor = r.incr('contador_global')
    print(f"Worker: Contador actualizado a {nuevo_valor}")
    time.sleep(1)
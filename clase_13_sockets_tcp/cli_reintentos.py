#!/usr/bin/env python3
import socket
import time

def conectar_con_reintentos(host, puerto, intentos=5):
    for intento in range(1, intentos + 1):
        try:
            print(f'Intento {intento}...')
            return socket.create_connection((host, puerto), timeout=2)
        except (ConnectionRefusedError, TimeoutError) as e:
            espera = 0.5 * intento
            print(f'  falló ({e}). Reintento en {espera}s')
            time.sleep(espera)
    raise ConnectionError(f'No se pudo conectar a {host}:{puerto}')

if __name__ == '__main__':
    with conectar_con_reintentos('localhost', 8080) as s:
        s.sendall(b'hola\n')
        print(f'Respuesta: {s.recv(4096)!r}')
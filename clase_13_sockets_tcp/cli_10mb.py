#!/usr/bin/env python3
import socket

datos = b'x' * (10 * 1024 * 1024)   # 10 MB
with socket.create_connection(('localhost', 8080)) as s:
    n = s.send(datos)
    print(f'send() devolvió: {n} de {len(datos)}')
#!/usr/bin/env python3
import socket

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.connect(('localhost', 8080))
    s.sendall(b'hola desde Python\n')
    print(f'Recibido: {s.recv(4096)!r}')
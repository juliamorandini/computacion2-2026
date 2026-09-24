#!/usr/bin/env python3
import socket

with socket.create_connection(('localhost', 8080)) as s:
    s.sendall(b'test\n')
    while True:
        datos = s.recv(4096)
        print(f'recv devolvió: {datos!r}')
        # FALTA el chequeo
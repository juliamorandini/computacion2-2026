#!/usr/bin/env python3
import socket

with socket.create_connection(('localhost', 8080)) as s:
    s.sendall(b'uno\ndos\ntres\n')
    s.shutdown(socket.SHUT_WR)     # avisamos que no mandamos más
    resp = b''
    while True:
        d = s.recv(4096)
        if not d: break
        resp += d
    print(f'Recibido: {resp!r}')
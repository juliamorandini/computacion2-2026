#!/usr/bin/env python3
import socket, time

with socket.create_connection(('localhost', 8080)) as s:
    for b in b'hola\n':
        s.sendall(bytes([b]))
        time.sleep(0.2)
    s.shutdown(socket.SHUT_WR)
    resp = b''
    while True:
        d = s.recv(4096)
        if not d: break
        resp += d
    print(f'Recibido: {resp!r}')

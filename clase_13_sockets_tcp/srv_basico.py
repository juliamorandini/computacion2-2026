#!/usr/bin/env python3
import socket

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(('0.0.0.0', 8080))
    srv.listen(5)
    print('Escuchando...')
    conn, dir = srv.accept()
    with conn:
        print(f'Conexión desde {dir}')
        datos = conn.recv(4096)
        conn.sendall(b'ECHO: ' + datos)
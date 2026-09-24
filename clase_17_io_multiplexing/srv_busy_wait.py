#!/usr/bin/env python3
"""Servidor con polling activo. Funciona, pero mal."""
import socket

srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
srv.bind(('localhost', 8080))
srv.listen(5)
srv.setblocking(False)

conexiones = []
print('Servidor busy-waiting en localhost:8080')
while True:
    try:
        conn, _ = srv.accept()
        conn.setblocking(False)
        conexiones.append(conn)
        print(f'+ cliente (total: {len(conexiones)})')
    except BlockingIOError:
        pass
    for c in list(conexiones):
        try:
            datos = c.recv(4096)
            if datos:
                c.sendall(datos)
            else:
                conexiones.remove(c)
                c.close()
                print(f'- cliente (total: {len(conexiones)})')
        except BlockingIOError:
            pass

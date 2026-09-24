#!/usr/bin/env python3
"""Servidor de eco: devuelve todo lo que recibe."""
import socket

HOST, PUERTO = '0.0.0.0', 8080

def atender(conn, direccion):
    print(f'Conexión desde {direccion}')
    try:
        while True:
            datos = conn.recv(4096)
            if not datos:
                print(f'{direccion} cerró')
                break
            print(f'recv() -> {datos!r}')
            conn.sendall(datos)
    except (ConnectionResetError, BrokenPipeError) as e:
        print(f'{direccion} se desconectó: {e}')

def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind((HOST, PUERTO))
        srv.listen(5)
        print(f'Escuchando en {HOST}:{PUERTO}...')
        while True:
            conn, dir = srv.accept()
            with conn:
                atender(conn, dir)

if __name__ == '__main__':
    main()
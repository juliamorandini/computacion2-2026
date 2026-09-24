#!/usr/bin/env python3
"""Servidor con framing por líneas (delimitador = \\n)."""
import socket

HOST, PUERTO = '0.0.0.0', 8080

def recibir_lineas(sock):
    """Generador de líneas completas desde un socket.
    Acumula bytes hasta encontrar \\n y entrega cada línea."""
    buffer = b''
    while True:
        pedazo = sock.recv(4096)
        if not pedazo:
            if buffer:
                print(f'Advertencia: datos incompletos al cerrar: {buffer!r}')
            return
        buffer += pedazo
        while b'\n' in buffer:
            linea, buffer = buffer.split(b'\n', 1)
            yield linea

def atender(conn, direccion):
    print(f'Conexión desde {direccion}')
    try:
        for linea in recibir_lineas(conn):
            print(f'línea: {linea!r}')
            respuesta = linea.upper() + b'\n'
            conn.sendall(respuesta)
    except (ConnectionResetError, BrokenPipeError) as e:
        print(f'{direccion} se desconectó: {e}')
    print(f'{direccion} terminó')

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
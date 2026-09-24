#!/usr/bin/env python3
"""Cliente de eco con varios modos de prueba."""
import argparse
import socket
import sys

def modo_parcial(host, puerto, chunk):
    with socket.create_connection((host, puerto)) as s:
        s.sendall(b'hola mundo\n')
        while True:
            pedazo = s.recv(chunk)
            if not pedazo:
                break
            print(f'recv({chunk}) devolvió: {pedazo!r}')

def modo_tres(host, puerto):
    with socket.create_connection((host, puerto)) as s:
        s.sendall(b'HOLA')
        s.sendall(b'COMO')
        s.sendall(b'ESTAS')
        # leemos hasta que el server cierre
        while True:
            d = s.recv(4096)
            if not d:
                break
            print(f'Cliente recibió: {d!r}')

def modo_normal(host, puerto):
    with socket.create_connection((host, puerto)) as s:
        s.sendall(b'hola mundo\n')
        print(f'Recibido: {s.recv(4096)!r}')

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--host', default='localhost')
    p.add_argument('--puerto', type=int, default=8080)
    p.add_argument('--parcial', action='store_true')
    p.add_argument('--chunk', type=int, default=4)
    p.add_argument('--tres', action='store_true')
    args = p.parse_args()

    if args.parcial:
        modo_parcial(args.host, args.puerto, args.chunk)
    elif args.tres:
        modo_tres(args.host, args.puerto)
    else:
        modo_normal(args.host, args.puerto)
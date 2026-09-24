#!/usr/bin/env python3
"""Abre N conexiones TCP y las deja abiertas."""
import socket
import sys

N = int(sys.argv[1]) if len(sys.argv) > 1 else 200
conns = []
for i in range(N):
    try:
        s = socket.create_connection(('localhost', 8080))
        conns.append(s)
        print(f'{i+1} abiertas')
    except Exception as e:
        print(f'falló en {i+1}: {e}')
        break
input('Enter para cerrar...')
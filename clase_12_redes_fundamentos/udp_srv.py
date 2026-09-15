#!/usr/bin/env python3
"""Receptor UDP: imprime cada datagrama que llega."""
import socket

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.bind(('localhost', 8080))
s.settimeout(5)

print("Esperando datagramas (5s de timeout)...")
try:
    while True:
        datos, origen = s.recvfrom(4096)
        print(f"recv: {datos!r} de {origen}")
except socket.timeout:
    print("(timeout, fin)")
#!/usr/bin/env python3
"""Servidor dual-stack: acepta IPv4 e IPv6 en el mismo socket."""
import socket
import sys

v6only = int(sys.argv[1]) if len(sys.argv) > 1 else 0

s = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, v6only)
s.bind(('::', 8080))
s.listen(5)
print(f'Escuchando en [::]:8080 con IPV6_V6ONLY={v6only}')
print(f'Implementación: {type(s).__name__}')

try:
    while True:
        conn, direccion = s.accept()
        print(f'+ conexión desde {direccion}')
        conn.sendall(b'OK\n')
        conn.close()
except KeyboardInterrupt:
    print('\nCortado')
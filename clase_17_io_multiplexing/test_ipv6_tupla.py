#!/usr/bin/env python3
import socket

s = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
s.bind(('::1', 0))
print('getsockname():', s.getsockname())
print('cantidad de elementos:', len(s.getsockname()))

try:
    host, puerto = s.getsockname()
    print('esto no debería llegar')
except ValueError as e:
    print('ValueError:', e)

# Forma portátil IPv4/IPv6:
info = s.getsockname()
print(f'Portátil: host={info[0]}, puerto={info[1]}')
s.close()

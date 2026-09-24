#!/usr/bin/env python3
import socket

r = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
r.bind(('localhost', 8081))

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.sendto(b'X' * 100, ('localhost', 8081))

datos, _ = r.recvfrom(10)          # buffer de 10 para un datagrama de 100
print(f'primer recvfrom: {len(datos)} bytes')

r.settimeout(1.0)
try:
    datos2, _ = r.recvfrom(65535)
    print(f'segundo recvfrom: {len(datos2)} bytes')
except TimeoutError:
    print('segundo recvfrom: nada')
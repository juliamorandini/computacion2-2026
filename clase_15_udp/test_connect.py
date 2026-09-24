#!/usr/bin/env python3
import socket
import sys

modo = sys.argv[1] if len(sys.argv) > 1 else 'connect'

if modo == 'connect':
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(2)
    s.connect(('localhost', 9999))     # puerto vacío
    s.send(b'hola')
    try:
        s.recv(4096)
    except ConnectionRefusedError:
        print('ConnectionRefusedError')
    except TimeoutError:
        print('timeout')
else:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(2)
    s.sendto(b'hola', ('localhost', 9999))
    try:
        s.recvfrom(4096)
    except TimeoutError:
        print('timeout')
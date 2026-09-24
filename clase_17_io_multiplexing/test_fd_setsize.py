#!/usr/bin/env python3
import select
import socket

relleno = [socket.socket() for _ in range(1100)]
alto = relleno[-1]
print(f'fd más alto: {alto.fileno()}')

try:
    select.select([alto], [], [], 0)
    print('select OK')
except ValueError as e:
    print(f'select FALLA: {e}')

# Repetir con poll
import select as s2
p = s2.poll()
p.register(alto, s2.POLLIN)
print(f'poll devolvió: {p.poll(0)}')

# Limpiar
for s in relleno:
    s.close()

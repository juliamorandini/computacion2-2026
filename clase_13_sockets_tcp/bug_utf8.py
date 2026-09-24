#!/usr/bin/env python3
datos = 'año'.encode('utf-8')       # b'a\xc3\xb1o'
print(f'bytes: {datos!r}')
print(f'primeros 2: {datos[:2]!r}')
try:
    print(datos[:2].decode('utf-8'))
except UnicodeDecodeError as e:
    print(f'ERROR: {e}') 
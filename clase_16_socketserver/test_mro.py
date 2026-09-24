#!/usr/bin/env python3
import socketserver

class Bien(socketserver.ThreadingMixIn, socketserver.TCPServer): pass
class Mal(socketserver.TCPServer, socketserver.ThreadingMixIn): pass

for C in (Bien, Mal):
    print(f'{C.__name__}:')
    print(f'  MRO: {[k.__name__ for k in C.__mro__][:4]}')
    proveedor = next(k.__name__ for k in C.__mro__
                     if 'process_request' in k.__dict__)
    print(f'  process_request viene de: {proveedor}')
    print()

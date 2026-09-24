#!/usr/bin/env python3
import inspect
import socketserver

print('=== ThreadingMixIn ===')
print(inspect.getsource(socketserver.ThreadingMixIn))

print('=== ForkingMixIn ===')
print(inspect.getsource(socketserver.ForkingMixIn))

print('=== ThreadingTCPServer ===')
print(inspect.getsource(socketserver.ThreadingTCPServer))

print('=== BaseServer.process_request ===')
print(inspect.getsource(socketserver.BaseServer.process_request))


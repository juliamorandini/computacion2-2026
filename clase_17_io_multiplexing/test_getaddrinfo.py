#!/usr/bin/env python3
import socket

for info in socket.getaddrinfo('google.com', 80, type=socket.SOCK_STREAM):
    print(info[0].name, info[4])

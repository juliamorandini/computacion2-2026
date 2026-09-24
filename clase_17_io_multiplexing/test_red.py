#!/usr/bin/env python3
import ipaddress

red = ipaddress.ip_network('192.168.1.0/24')
print(ipaddress.ip_address('192.168.1.37') in red)
print(ipaddress.ip_address('192.168.2.10') in red)
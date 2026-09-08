#!/bin/bash
echo "--- Interfaces ---"
ip addr show

echo -e "\n--- Rutas ---"
ip route

echo -e "\n--- Puertos ---"
ss -tlnp
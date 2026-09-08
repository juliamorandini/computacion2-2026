#!/bin/bash
echo "--- IP y TTL de la UM ---"
dig www.um.edu.ar

echo -e "\n--- Múltiples IPs de Google ---"
dig google.com +short

echo -e "\n--- Tiempos de Caché (Ejecuciones seguidas) ---"
dig google.com | grep "Query time"
dig google.com | grep "Query time"
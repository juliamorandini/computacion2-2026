#!/usr/bin/env bash
# correr_mediciones.sh - Corre las tres mediciones obligatorias (M1, M2, M3).
#
# Rearranca la API con la configuración que pide cada corrida (variables de
# entorno que el docker-compose.yml interpola) y ejecuta el script de
# medición dentro del servicio 'mediciones'.  Los resultados quedan en
# mediciones/resultados/*.md.  Tarda unos 10 minutos.
#
# Uso (desde TP2/):
#   bash mediciones/correr_mediciones.sh

set -euo pipefail
cd "$(dirname "$0")/.."

# ---- Helpers ---- #

# levantar VAR=valor ... : recrea la api con esa configuración (registro vacío)
levantar() {
    env "$@" docker compose up -d --force-recreate api >/dev/null 2>&1
    echo ">> api con: ${*:-defaults}"
}

medir() {
    docker compose run --rm mediciones python "$@"
}

# ---- Preparación ---- #

rm -f mediciones/resultados/m1_io.md mediciones/resultados/m2_bloqueo.md mediciones/resultados/m3_techo.md
docker compose build >/dev/null
docker compose --profile mediciones build >/dev/null
docker compose up -d servidor_lento >/dev/null 2>&1

NUCLEOS=$(docker run --rm python:3.11-slim nproc)
echo "Núcleos visibles en el contenedor: $NUCLEOS"

# ---- M1: concurrencia I/O ---- #

levantar MAX_DESCARGAS_SIMULTANEAS=10
medir medir_io.py --etiqueta "MAX_DESCARGAS_SIMULTANEAS=10"
levantar MAX_DESCARGAS_SIMULTANEAS=20
medir medir_io.py --etiqueta "MAX_DESCARGAS_SIMULTANEAS=20"

# ---- M2: event loop bloqueado ---- #

levantar HASH_EN_EXECUTOR=0
medir medir_bloqueo.py --etiqueta "sin executor, HASH_EN_EXECUTOR=0"
levantar HASH_EN_EXECUTOR=1
medir medir_bloqueo.py --etiqueta "con executor, HASH_EN_EXECUTOR=1"

# ---- M3: techo del pool ---- #

# a) Configuración por defecto: ¿qué pasa al subir N?
levantar WORKERS=4 COLA_MAX=100
medir medir_techo.py --tipo esperar --segundos 1 --ns 1,10,50,100,200,500,1000,10000 \
    --etiqueta "WORKERS=4, COLA_MAX=100"

# b) Cola sin tope práctico, variando WORKERS con N fijo
for w in 10 100 1000; do
    levantar WORKERS=$w COLA_MAX=100000
    medir medir_techo.py --tipo esperar --segundos 1 --ns 1000 \
        --etiqueta "WORKERS=$w, COLA_MAX=100000"
done

# c) Workers de sobra: ¿dónde está el techo del propio event loop?
levantar WORKERS=10000 COLA_MAX=100000
medir medir_techo.py --tipo esperar --segundos 1 --ns 1000,5000,10000 \
    --etiqueta "WORKERS=10000, COLA_MAX=100000"

# d) CPU-bound: 32 hashes, variando los procesos del executor
for p in 1 2 4 8 16; do
    levantar WORKERS=32 COLA_MAX=1000 PROCESOS_CPU=$p
    medir medir_techo.py --tipo hashear --iteraciones 1000000 --ns 32 \
        --etiqueta "WORKERS=32, PROCESOS_CPU=$p"
done

# ---- Cierre ---- #

levantar
echo "Listo. Resultados en mediciones/resultados/"

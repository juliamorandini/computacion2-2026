"""config.py - Configuración centralizada por variables de entorno.

Todas las variables tienen defaults razonables para desarrollo local.
En producción se setean vía docker-compose.yml (sección environment).
"""

import os

# ---- Pool de workers ---- #
WORKERS = int(os.getenv('WORKERS', '4'))

# ---- Cola ---- #
COLA_MAX = int(os.getenv('COLA_MAX', '100'))

# ---- CPU-bound ---- #
PROCESOS_CPU = int(os.getenv('PROCESOS_CPU', '2'))
HASH_EN_EXECUTOR = os.getenv('HASH_EN_EXECUTOR', '1') == '1'
TAMANO_BLOQUE_HASH = int(os.getenv('TAMANO_BLOQUE_HASH', '100000'))

# ---- Timeouts y apagado ---- #
TIMEOUT_DEFAULT = float(os.getenv('TIMEOUT_DEFAULT', '30'))
LIMITE_APAGADO = float(os.getenv('LIMITE_APAGADO', '10'))

# ---- Persistencia ---- #
DIR_ESTADO = os.getenv('DIR_ESTADO', './estado')

# ---- Red ---- #
MAX_DESCARGAS_SIMULTANEAS = int(os.getenv('MAX_DESCARGAS_SIMULTANEAS', '10'))

"""persistencia.py - Volcado y detección de estado previo.

Al apagar (SIGTERM/SIGINT), vuelca el registro a estado_<timestamp>.json.
Al arrancar, busca volcados previos y los reporta por log.

La consigna pide solo reportar, no restaurar.
"""

from __future__ import annotations

import json
import os
import glob
import logging
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from registro import Registro

logger = logging.getLogger(__name__)


def volcar_estado(registro: Registro, directorio: str) -> str:
    """Escribe el estado actual a un archivo JSON con timestamp.

    Args:
        registro: Registro de tareas.
        directorio: Directorio donde guardar el volcado.

    Returns:
        Ruta del archivo creado.
    """
    os.makedirs(directorio, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    ruta = os.path.join(directorio, f'estado_{timestamp}.json')

    datos = {
        'timestamp': timestamp,
        'tareas': [t.a_dict_volcado() for t in registro.todas()],
    }

    with open(ruta, 'w', encoding='utf-8') as f:
        json.dump(datos, f, indent=2, ensure_ascii=False)

    logger.info('Estado volcado a %s (%d tareas)', ruta, len(datos['tareas']))
    return ruta


def reportar_volcado_previo(directorio: str) -> None:
    """Busca el volcado más reciente y lo reporta por log.

    Si no existe el directorio o no hay volcados, no hace nada.
    """
    patron = os.path.join(directorio, 'estado_*.json')
    archivos = sorted(glob.glob(patron))

    if not archivos:
        logger.info('No se encontraron volcados previos en %s', directorio)
        return

    ultimo = archivos[-1]
    try:
        with open(ultimo, 'r', encoding='utf-8') as f:
            datos = json.load(f)

        tareas = datos.get('tareas', [])
        conteos = {}
        for t in tareas:
            estado = t.get('estado', 'desconocido')
            conteos[estado] = conteos.get(estado, 0) + 1

        logger.info(
            'Volcado previo encontrado: %s (%d tareas: %s)',
            ultimo,
            len(tareas),
            ', '.join(f'{k}={v}' for k, v in sorted(conteos.items())),
        )
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning('No se pudo leer el volcado previo %s: %s', ultimo, exc)

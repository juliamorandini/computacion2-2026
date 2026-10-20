"""registro.py - Registro en memoria de todas las tareas.

Almacena las tareas en un dict[str, Tarea].  No necesita Lock porque
todas las mutaciones ocurren en el hilo del event loop y ninguna sección
crítica tiene un await en el medio — el cambio de contexto solo ocurre
en un await (clase 20, "Por qué no hacen falta locks").
"""

from __future__ import annotations

import time
import logging
from typing import Optional

from modelos import Estado, Tarea

logger = logging.getLogger(__name__)


class Registro:
    """Almacén central de tareas.

    Cada método que muta estado lo hace de forma atómica dentro de un
    tramo síncrono (sin await), así que es seguro sin locks.
    """

    def __init__(self):
        self._tareas: dict[str, Tarea] = {}

    # ---- Consultas ---- #

    def obtener(self, id: str) -> Optional[Tarea]:
        """Devuelve la tarea o None si no existe."""
        return self._tareas.get(id)

    def listar(self, estado: Optional[Estado] = None) -> list[dict]:
        """Lista tareas, opcionalmente filtradas por estado."""
        if estado is not None:
            return [t.a_dict() for t in self._tareas.values() if t.estado == estado]
        return [t.a_dict() for t in self._tareas.values()]

    def estadisticas(self, ocupados: int) -> dict:
        """Totales por estado, tiempos promedio y workers ocupados."""
        totales = {e.value: 0 for e in Estado}
        tiempos: list[float] = []

        for t in self._tareas.values():
            totales[t.estado.value] += 1
            if t.iniciada_en is not None and t.terminada_en is not None:
                tiempos.append(t.terminada_en - t.iniciada_en)

        return {
            'totales': totales,
            'tiempo_promedio': sum(tiempos) / len(tiempos) if tiempos else 0,
            'workers_ocupados': ocupados,
            'total_tareas': len(self._tareas),
        }

    # ---- Mutaciones (todas sin await) ---- #

    def registrar(self, tarea: Tarea) -> None:
        """Agrega una tarea nueva con estado PENDIENTE."""
        # Sin await: atómico respecto al event loop
        self._tareas[tarea.id] = tarea
        logger.info('Tarea %s registrada como %s', tarea.id, tarea.estado.value)

    def marcar_ejecutando(self, id: str) -> None:
        """Transiciona a EJECUTANDO y registra el timestamp."""
        t = self._tareas[id]
        t.estado = Estado.EJECUTANDO
        t.iniciada_en = time.time()

    def marcar_completada(self, id: str, resultado) -> None:
        """Transiciona a COMPLETADA con resultado."""
        t = self._tareas[id]
        t.estado = Estado.COMPLETADA
        t.resultado = resultado
        t.terminada_en = time.time()

    def marcar_fallida(self, id: str, error: str) -> None:
        """Transiciona a FALLIDA con motivo."""
        t = self._tareas[id]
        t.estado = Estado.FALLIDA
        t.error = error
        t.terminada_en = time.time()

    def marcar_cancelada(self, id: str, motivo: str = 'cancelada por el usuario') -> None:
        """Transiciona a CANCELADA con motivo."""
        t = self._tareas[id]
        t.estado = Estado.CANCELADA
        t.error = motivo
        t.terminada_en = time.time()

    def todas(self) -> list[Tarea]:
        """Devuelve todas las tareas (para volcado de estado)."""
        return list(self._tareas.values())

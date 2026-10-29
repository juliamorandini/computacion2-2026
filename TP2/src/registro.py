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
        """Totales por estado, tiempos promedio y workers ocupados.

        Dos tiempos promedio, en segundos:
          - ejecucion: de iniciada a terminada, solo de las completadas.
            Una cancelada o una que venció su timeout no dice cuánto tarda
            una tarea, así que no entra en el promedio.
          - espera_en_cola: de creada a iniciada, de todas las que ya
            arrancaron.  Es el número que crece cuando faltan workers (M3).
        """
        totales = {e.value: 0 for e in Estado}
        ejecucion: list[float] = []
        espera: list[float] = []

        for t in self._tareas.values():
            totales[t.estado.value] += 1
            if t.iniciada_en is not None:
                espera.append(t.iniciada_en - t.creada_en)
            if t.estado == Estado.COMPLETADA:
                ejecucion.append(t.terminada_en - t.iniciada_en)

        return {
            'totales': totales,
            'tiempos_promedio': {
                'ejecucion': _promedio(ejecucion),
                'espera_en_cola': _promedio(espera),
            },
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


def _promedio(valores: list[float]) -> float:
    return sum(valores) / len(valores) if valores else 0

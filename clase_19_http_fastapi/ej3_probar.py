#!/usr/bin/env python3
"""Clase 19 - Ejercicio 3: provoca los errores y prueba los endpoints nuevos.

Usa el TestClient de FastAPI (no hace falta levantar el servidor).

Uso:
    python3 ej3_probar.py
"""
from fastapi.testclient import TestClient

import ej3_api

cliente = TestClient(ej3_api.app)


def mostrar(titulo, r):
    print(f'\n{titulo}\n  -> {r.status_code}  {r.text[:260]}')


print('=== Parte B: los cuatro errores ===')
mostrar('GET /tareas/abc  (el print de obtener() NO debe aparecer)',
        cliente.get('/tareas/abc'))
mostrar("POST tipo='volar'", cliente.post('/tareas', json={'tipo': 'volar'}))
mostrar("POST tipo='esperar', prioridad=99",
        cliente.post('/tareas', json={'tipo': 'esperar', 'prioridad': 99}))
mostrar('GET /tareas/999  (el print SI aparece: la validacion paso)',
        cliente.get('/tareas/999'))

print('\n=== Parte C ===')
r = cliente.post('/tareas', json={'tipo': 'esperar'})
mostrar('POST valido', r)
mostrar('PATCH /tareas/1 estado=ejecutando',
        cliente.patch('/tareas/1', json={'estado': 'ejecutando'}))
mostrar('PATCH /tareas/1 estado invalido',
        cliente.patch('/tareas/1', json={'estado': 'volando'}))
mostrar('PATCH /tareas/77 (no existe)',
        cliente.patch('/tareas/77', json={'estado': 'completada'}))
mostrar('GET /estadisticas', cliente.get('/estadisticas'))

for _ in range(10):                 # llegar a 10 pendientes
    cliente.post('/tareas', json={'tipo': 'hashear'})
mostrar('GET /estadisticas con 10 pendientes', cliente.get('/estadisticas'))
r = cliente.post('/tareas', json={'tipo': 'hashear'})
mostrar('POST con 10 pendientes', r)
print(f"  header Retry-After: {r.headers.get('retry-after')}")


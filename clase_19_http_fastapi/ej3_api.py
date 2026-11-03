#!/usr/bin/env python3
"""Clase 19 - Ejercicio 3 (obligatorio): API con FastAPI.

Es api.py de la clase extendida con:
  - PATCH /tareas/{id}       cambia solo el estado (modelo con campos opcionales)
  - GET   /estadisticas      cantidad de tareas por estado
  - POST  /tareas            rechaza con 429 si ya hay 10 pendientes

Uso:
    python3 ej3_api.py          # levanta en http://localhost:8000/docs
    python3 ej3_probar.py       # provoca los errores y muestra codigo y mensaje

-----------------------------------------------------------------------
RESPUESTAS
-----------------------------------------------------------------------

Parte A
  1. La documentacion de /docs no la escribi yo: la genera FastAPI (Swagger
     UI) a partir de las rutas, los modelos Pydantic, los tipos y los
     docstrings.
  2. Un tipo fuera de la lista (Literal) devuelve 422 y el mensaje
     "Input should be 'descargar', 'hashear' or 'esperar'".
  3. /openapi.json es la descripcion de la API en formato OpenAPI (JSON):
     rutas, parametros, esquemas y respuestas. Swagger UI se dibuja a
     partir de ese archivo; sirve tambien para generar clientes.

Parte B (codigos medidos con ej3_probar.py)
  4. GET  /tareas/abc                       -> 422 "Input should be a valid
                                               integer, unable to parse string
                                               as an integer"  (loc: path, tarea_id)
     POST tipo='volar'                      -> 422 "Input should be
                                               'descargar', 'hashear' or 'esperar'"
     POST tipo='esperar', prioridad=99      -> 422 "Input should be less than
                                               or equal to 5"
     GET  /tareas/999                       -> 404 {"detail": "No existe esa tarea"}
  5. Tres dan 422 y una da 404. 422 = la peticion esta mal formada: no
     cumple el esquema (lo decide Pydantic ANTES de llamar a mi funcion).
     404 = la peticion es valida pero el recurso no existe (lo decide mi
     codigo con HTTPException).
  6. 'loc' es la ubicacion del error: de donde vino el dato y cual campo,
     por ejemplo ['path', 'tarea_id'] o ['body', 'prioridad'].
  7. La validacion corre ANTES de la funcion: el print dentro de obtener()
     NO aparece cuando se pide /tareas/abc, y si aparece con /tareas/999.

Parte C
  8-9. Implementados abajo (PATCH con TareaParche, todos los campos
       opcionales; /estadisticas cuenta por estado, incluyendo los 0).
  10. Elegi 429 Too Many Requests: el cliente esta mandando mas de lo que el
      servidor acepta ahora y puede reintentar cuando haya lugar (la
      peticion es valida, no es un conflicto de datos como 409 ni una caida
      del servicio como 503). Se acompana de un header Retry-After.

Parte D
  11. Sin ': int' el parametro llega como str: /tareas/abc ya no da 422, pasa
      a mi funcion y da 404 (y /tareas/1 no encuentra la clave 1 porque la
      clave del dict es int, tambien 404). Se pierde la validacion.
  12. Con 'prioridad: str' acepta cualquier texto ("alta", "xyz") y deja de
      aceptar el numero 3 (Pydantic v2 no convierte int a str: 422
      "Input should be a valid string"). Ya no se valida el rango.
  13. Con cada anotacion de tipo FastAPI: (1) VALIDA el dato recibido,
      (2) CONVIERTE al tipo (ej. '5' -> 5) y (3) DOCUMENTA (OpenAPI/docs).
"""
from typing import Literal

from fastapi import FastAPI, HTTPException, Query, Response
from pydantic import BaseModel, Field

app = FastAPI(
    title='Tareas',
    description='Ejercicio 3 de la clase 19: HTTP + FastAPI',
)

ESTADOS = ('pendiente', 'ejecutando', 'completada')
MAX_PENDIENTES = 10

tareas: dict[int, dict] = {}
proximo_id = 0


class TareaNueva(BaseModel):
    tipo: Literal['descargar', 'hashear', 'esperar']
    prioridad: int = Field(default=1, ge=1, le=5,
                           description='1 = más baja, 5 = más alta')


class Tarea(TareaNueva):
    id: int
    estado: Literal['pendiente', 'ejecutando', 'completada'] = 'pendiente'


class TareaParche(BaseModel):
    """Modelo para PATCH: todos los campos son opcionales.
    Solo se aplican los que vienen; por ahora se permite cambiar el estado."""
    estado: Literal['pendiente', 'ejecutando', 'completada'] | None = None


@app.get('/')
async def raiz():
    return {'servicio': 'tareas', 'docs': '/docs'}


@app.get('/tareas', response_model=list[Tarea])
async def listar(
    estado: str | None = Query(default=None, description='Filtrar por estado'),
    limite: int = Query(default=10, ge=1, le=100),
):
    items = list(tareas.values())
    if estado:
        items = [t for t in items if t['estado'] == estado]
    return items[:limite]


@app.post('/tareas', response_model=Tarea, status_code=201)
async def crear(nueva: TareaNueva, respuesta: Response):
    global proximo_id
    pendientes = sum(1 for t in tareas.values() if t['estado'] == 'pendiente')
    if pendientes >= MAX_PENDIENTES:
        # 429: el cliente puede reintentar cuando se libere lugar.
        raise HTTPException(
            status_code=429,
            detail=f'Hay {pendientes} tareas pendientes (máximo {MAX_PENDIENTES})',
            headers={'Retry-After': '5'},
        )
    proximo_id += 1
    tarea = {'id': proximo_id, **nueva.model_dump(), 'estado': 'pendiente'}
    tareas[proximo_id] = tarea
    return tarea


@app.get('/tareas/{tarea_id}', response_model=Tarea)
async def obtener(tarea_id: int):
    # Ejercicio 7: este print solo aparece si la validacion de tarea_id paso.
    print(f'  [obtener] se ejecuta mi funcion con tarea_id={tarea_id!r}')
    if tarea_id not in tareas:
        raise HTTPException(status_code=404, detail='No existe esa tarea')
    return tareas[tarea_id]


@app.patch('/tareas/{tarea_id}', response_model=Tarea)
async def modificar(tarea_id: int, cambios: TareaParche):
    if tarea_id not in tareas:
        raise HTTPException(status_code=404, detail='No existe esa tarea')
    # exclude_unset: solo lo que el cliente mando de verdad.
    tareas[tarea_id].update(cambios.model_dump(exclude_unset=True, exclude_none=True))
    return tareas[tarea_id]


@app.get('/estadisticas')
async def estadisticas():
    cuenta = {e: 0 for e in ESTADOS}
    for t in tareas.values():
        cuenta[t['estado']] += 1
    return {'total': len(tareas), 'por_estado': cuenta}


@app.delete('/tareas/{tarea_id}', status_code=204)
async def borrar(tarea_id: int):
    if tarea_id not in tareas:
        raise HTTPException(status_code=404, detail='No existe esa tarea')
    del tareas[tarea_id]


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='127.0.0.1', port=8000)

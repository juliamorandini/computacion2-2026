## M1 — Concurrencia I/O (MAX_DESCARGAS_SIMULTANEAS=10)

20 URLs del servidor lento con demoras de 0.20 a 1.15 s (suma teórica 13.50 s, la más lenta 1.15 s). Mediana de 3 corridas.

| Modo | Mediana (s) | Mín (s) | Máx (s) |
|---|---|---|---|
| Secuencial (`for` + `await`) | 13.59 | 13.58 | 13.59 |
| Concurrente (`asyncio.gather`) | 1.17 | 1.16 | 1.17 |

**Speedup: 11.7x**

De punta a punta, una tarea `descargar` con las mismas 20 URLs:

| Tiempo de la tarea (s) | Descarga más lenta (s) | Suma de las 20 (s) |
|---|---|---|
| 1.83 | 1.15 | 13.67 |

## M1 — Concurrencia I/O (MAX_DESCARGAS_SIMULTANEAS=20)

20 URLs del servidor lento con demoras de 0.20 a 1.15 s (suma teórica 13.50 s, la más lenta 1.15 s). Mediana de 3 corridas.

| Modo | Mediana (s) | Mín (s) | Máx (s) |
|---|---|---|---|
| Secuencial (`for` + `await`) | 13.58 | 13.57 | 13.58 |
| Concurrente (`asyncio.gather`) | 1.16 | 1.16 | 1.17 |

**Speedup: 11.7x**

De punta a punta, una tarea `descargar` con las mismas 20 URLs:

| Tiempo de la tarea (s) | Descarga más lenta (s) | Suma de las 20 (s) |
|---|---|---|
| 1.19 | 1.17 | 13.85 |


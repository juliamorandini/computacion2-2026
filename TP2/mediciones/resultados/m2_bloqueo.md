## M2 — Event loop con hash pesado (sin executor, HASH_EN_EXECUTOR=0)

`hashear` de 14,000,000 iteraciones: tardó 4.74 s (estado final: completada). GET /tareas cada 50 ms.

| Momento | GETs | Mediana (ms) | p95 (ms) | Máx (ms) |
|---|---|---|---|---|
| API ociosa | 40 | 1.7 | 2.8 | 3.8 |
| Durante el hash | 94 | 2389.4 | 4462.5 | 4691.7 |

## M2 — Event loop con hash pesado (con executor, HASH_EN_EXECUTOR=1)

`hashear` de 14,000,000 iteraciones: tardó 4.88 s (estado final: completada). GET /tareas cada 50 ms.

| Momento | GETs | Mediana (ms) | p95 (ms) | Máx (ms) |
|---|---|---|---|---|
| API ociosa | 40 | 2.0 | 3.2 | 4.5 |
| Durante el hash | 98 | 1.5 | 2.1 | 3.7 |


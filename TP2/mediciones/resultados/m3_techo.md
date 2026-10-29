## M3 — `esperar` de 1.0 s (WORKERS=4, COLA_MAX=100)

| N | Aceptadas | 503 | Error de conexión | POST mediana (ms) | POST máx (ms) | Total (s) | Throughput (tareas/s) | Espera en cola mediana (s) | Espera en cola máx (s) |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 1 | 0 | 0 | 3 | 3 | 1.02 | 1.0 | 0.00 | 0.00 |
| 10 | 10 | 0 | 0 | 12 | 13 | 3.11 | 3.2 | 1.00 | 2.00 |
| 50 | 50 | 0 | 0 | 26 | 47 | 13.07 | 3.8 | 5.99 | 11.97 |
| 100 | 100 | 0 | 0 | 73 | 139 | 25.14 | 4.0 | 11.95 | 23.91 |
| 200 | 104 | 96 | 0 | 147 | 296 | 26.15 | 4.0 | 12.45 | 24.90 |
| 500 | 104 | 396 | 0 | 381 | 740 | 26.17 | 4.0 | 12.45 | 24.90 |
| 1000 | 108 | 892 | 0 | 914 | 1740 | 27.25 | 4.0 | 12.94 | 25.03 |
| 10000 | 196 | 9804 | 0 | 16729 | 26710 | 52.12 | 3.8 | 23.74 | 25.03 |

## M3 — `esperar` de 1.0 s (WORKERS=10, COLA_MAX=100000)

| N | Aceptadas | 503 | Error de conexión | POST mediana (ms) | POST máx (ms) | Total (s) | Throughput (tareas/s) | Espera en cola mediana (s) | Espera en cola máx (s) |
|---|---|---|---|---|---|---|---|---|---|
| 1000 | 1000 | 0 | 0 | 800 | 1591 | 100.29 | 10.0 | 48.84 | 97.69 |

## M3 — `esperar` de 1.0 s (WORKERS=100, COLA_MAX=100000)

| N | Aceptadas | 503 | Error de conexión | POST mediana (ms) | POST máx (ms) | Total (s) | Throughput (tareas/s) | Espera en cola mediana (s) | Espera en cola máx (s) |
|---|---|---|---|---|---|---|---|---|---|
| 1000 | 1000 | 0 | 0 | 755 | 1437 | 10.26 | 97.5 | 3.88 | 7.81 |

## M3 — `esperar` de 1.0 s (WORKERS=1000, COLA_MAX=100000)

| N | Aceptadas | 503 | Error de conexión | POST mediana (ms) | POST máx (ms) | Total (s) | Throughput (tareas/s) | Espera en cola mediana (s) | Espera en cola máx (s) |
|---|---|---|---|---|---|---|---|---|---|
| 1000 | 1000 | 0 | 0 | 784 | 1493 | 2.56 | 391.0 | 0.00 | 0.00 |

## M3 — `esperar` de 1.0 s (WORKERS=10000, COLA_MAX=100000)

| N | Aceptadas | 503 | Error de conexión | POST mediana (ms) | POST máx (ms) | Total (s) | Throughput (tareas/s) | Espera en cola mediana (s) | Espera en cola máx (s) |
|---|---|---|---|---|---|---|---|---|---|
| 1000 | 1000 | 0 | 0 | 743 | 1399 | 2.46 | 406.5 | 0.00 | 0.00 |
| 5000 | 5000 | 0 | 0 | 5663 | 11743 | 12.83 | 389.8 | 0.00 | 0.03 |
| 10000 | 10000 | 0 | 0 | 17084 | 29969 | 31.34 | 319.1 | 0.00 | 0.00 |

## M3 — `hashear` de 1,000,000 iteraciones (WORKERS=32, PROCESOS_CPU=1)

| N | Aceptadas | 503 | Error de conexión | POST mediana (ms) | POST máx (ms) | Total (s) | Throughput (tareas/s) | Espera en cola mediana (s) | Espera en cola máx (s) |
|---|---|---|---|---|---|---|---|---|---|
| 32 | 32 | 0 | 0 | 32 | 44 | 10.44 | 3.1 | 0.00 | 0.00 |

## M3 — `hashear` de 1,000,000 iteraciones (WORKERS=32, PROCESOS_CPU=2)

| N | Aceptadas | 503 | Error de conexión | POST mediana (ms) | POST máx (ms) | Total (s) | Throughput (tareas/s) | Espera en cola mediana (s) | Espera en cola máx (s) |
|---|---|---|---|---|---|---|---|---|---|
| 32 | 32 | 0 | 0 | 37 | 50 | 5.78 | 5.5 | 0.00 | 0.00 |

## M3 — `hashear` de 1,000,000 iteraciones (WORKERS=32, PROCESOS_CPU=4)

| N | Aceptadas | 503 | Error de conexión | POST mediana (ms) | POST máx (ms) | Total (s) | Throughput (tareas/s) | Espera en cola mediana (s) | Espera en cola máx (s) |
|---|---|---|---|---|---|---|---|---|---|
| 32 | 32 | 0 | 0 | 32 | 41 | 3.01 | 10.6 | 0.00 | 0.00 |

## M3 — `hashear` de 1,000,000 iteraciones (WORKERS=32, PROCESOS_CPU=8)

| N | Aceptadas | 503 | Error de conexión | POST mediana (ms) | POST máx (ms) | Total (s) | Throughput (tareas/s) | Espera en cola mediana (s) | Espera en cola máx (s) |
|---|---|---|---|---|---|---|---|---|---|
| 32 | 32 | 0 | 0 | 39 | 49 | 2.04 | 15.7 | 0.00 | 0.00 |

## M3 — `hashear` de 1,000,000 iteraciones (WORKERS=32, PROCESOS_CPU=16)

| N | Aceptadas | 503 | Error de conexión | POST mediana (ms) | POST máx (ms) | Total (s) | Throughput (tareas/s) | Espera en cola mediana (s) | Espera en cola máx (s) |
|---|---|---|---|---|---|---|---|---|---|
| 32 | 32 | 0 | 0 | 86 | 96 | 1.48 | 21.7 | 0.01 | 0.02 |


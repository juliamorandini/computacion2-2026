def atender(conn, direccion):
    global clientes_activos, pico_simultaneos
    # with lock:
    #     clientes_activos += 1
    #     pico_simultaneos = max(pico_simultaneos, clientes_activos)
    clientes_activos += 1
    pico_simultaneos = max(pico_simultaneos, clientes_activos)
    try:
        ...
    finally:
        # with lock:
        #     clientes_activos -= 1
        clientes_activos -= 1
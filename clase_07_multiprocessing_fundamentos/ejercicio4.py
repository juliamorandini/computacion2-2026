import multiprocessing

def hijo(conn):
    for _ in range(5):
        msg = conn.recv()
        print(f"Hijo recibió: {msg}")
        conn.send("pong")
    conn.close()

if __name__ == "__main__":
    extremo_padre, extremo_hijo = multiprocessing.Pipe()
    p = multiprocessing.Process(target=hijo, args=(extremo_hijo,))
    p.start()

    for _ in range(5):
        extremo_padre.send("ping")
        respuesta = extremo_padre.recv()
        print(f"Padre recibió: {respuesta}")

    p.join()
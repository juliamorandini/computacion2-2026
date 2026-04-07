#!/usr/bin/env python3
"""Mini-shell: paso 2 - fork+exec."""
import os

def main():
    while True:
        try:
            linea = input("minish$ ")
        except EOFError:
            print("\nChau!")
            break

        linea = linea.strip()
        if not linea:
            continue

        if linea == "exit":
            break

        # Parsear comando y argumentos
        partes = linea.split()
        comando = partes[0]
        args = partes[1:]

        # Fork + exec
        pid = os.fork()

        if pid == 0:
            try:
                os.execvp(comando, [comando] + args)
            except OSError as e:
                print(f"minish: {comando}: {e}")
                os._exit(127)
        else:
            _, status = os.wait()
            # Opcional: mostrar código si no es 0
            codigo = os.WEXITSTATUS(status)
            if codigo != 0:
                print(f"[código {codigo}]")

if __name__ == "__main__":
    main()
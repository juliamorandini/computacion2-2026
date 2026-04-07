#!/usr/bin/env python3
"""Mini-shell: paso 1 - loop básico."""
import os

def main():
    while True:
        try:
            linea = input("minish$ ")
        except EOFError:
            print("\nChau!")
            break

        if not linea.strip():
            continue

        if linea.strip() == "exit":
            break

        print(f"Comando recibido: {linea}")

if __name__ == "__main__":
    main()
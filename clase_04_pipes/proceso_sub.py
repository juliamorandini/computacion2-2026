#!/usr/bin/env python3
"""Procesar texto usando pipeline de subprocess."""
import subprocess

texto = """
primera linea
segunda linea con error
tercera linea
otra linea con error
ultima linea
"""

# Pipeline: echo texto | grep error | wc -l
# Usando subprocess para construir el pipeline

echo = subprocess.Popen(
    ["echo", texto],
    stdout=subprocess.PIPE
)

grep = subprocess.Popen(
    ["grep", "error"],
    stdin=echo.stdout,
    stdout=subprocess.PIPE
)

wc = subprocess.Popen(
    ["wc", "-l"],
    stdin=grep.stdout,
    stdout=subprocess.PIPE,
    text=True
)

# Importante: cerrar pipes del padre
echo.stdout.close()
grep.stdout.close()

resultado, _ = wc.communicate()
print(f"Líneas con 'error': {resultado.strip()}")
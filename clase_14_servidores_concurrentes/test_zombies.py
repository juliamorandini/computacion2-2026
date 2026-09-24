#!/usr/bin/env python3
import os, signal, subprocess, time

recogidos = [0]

def cosechar(signum, frame):
    try:
        pid, _ = os.waitpid(-1, os.WNOHANG)   # SIN bucle
        if pid > 0:
            recogidos[0] += 1
    except ChildProcessError:
        pass

signal.signal(signal.SIGCHLD, cosechar)

N = 60
for _ in range(N):
    if os.fork() == 0:
        time.sleep(0.5)     # todos duermen lo mismo: mueren juntos
        os._exit(0)

time.sleep(2.0)
salida = subprocess.run(['ps', '--ppid', str(os.getpid()), '-o', 'stat='],
                        capture_output=True, text=True).stdout
zombies = sum(1 for l in salida.splitlines() if l.strip().startswith('Z'))
print(f'hijos={N}  recogidos={recogidos[0]}  zombies={zombies}')

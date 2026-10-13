import os
import time

from fastapi import FastAPI, Query

app = FastAPI(
    title="CPU-bound App",
    description="Aplicação para gerar carga de CPU",
)


@app.get("/health")
def health():
    return {"status": "ok", "app": "cpu-bound", "cpu_count": os.cpu_count()}


def eh_primo(numero: int) -> bool:
    if numero < 2:
        return False

    divisor = 2

    while divisor * divisor <= numero:
        if numero % divisor == 0:
            return False

        divisor += 1

    return True


@app.get("/cpu")
def cpu(n: int = Query(default=100_000, ge=1_000, le=2_000_000)):
    inicio = time.perf_counter()

    quantidade_primos = 0

    for numero in range(2, n + 1):
        if eh_primo(numero):
            quantidade_primos += 1

    tempo_ms = (time.perf_counter() - inicio) * 1000

    return {"n": n, "primos": quantidade_primos, "tempo_ms": round(tempo_ms, 2)}
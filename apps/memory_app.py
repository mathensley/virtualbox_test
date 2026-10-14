import asyncio
import os
import time

from fastapi import FastAPI, Query

app = FastAPI(
    title="Memory-bound App",
    description="Aplicação para gerar carga de memória RAM",
)


@app.get("/health")
def health():
    return {"status": "ok", "app": "memory-bound", "cpu_count": os.cpu_count()}


@app.get("/memory")
async def memory(
    mb: int = Query(default=100, ge=1, le=512), hold_ms: int = Query(default=1000, ge=0, le=5000)):
    inicio = time.perf_counter()

    tamanho = mb * 1024 * 1024

    dados = bytearray(tamanho)

    # Toca uma posição de cada página de memória.
    for posicao in range(0, tamanho, 4096):
        dados[posicao] = 1

    # Mantém a memória ocupada por um tempo.
    await asyncio.sleep(hold_ms / 1000)

    tempo_ms = (time.perf_counter() - inicio) * 1000

    return {"memoria_alocada_mb": mb, "hold_ms": hold_ms, "tempo_ms": round(tempo_ms, 2)}
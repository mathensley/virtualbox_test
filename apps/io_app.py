import os
import tempfile
import time

from fastapi import FastAPI, Query

app = FastAPI(
    title="I/O-bound App",
    description="Aplicação para gerar carga de entrada/saída em disco",
)


@app.get("/health")
def health():
    return {"status": "ok", "app": "io-bound", "cpu_count": os.cpu_count()}


@app.get("/io")
def io(
    mb: int = Query(default=20, ge=1, le=200)):
    inicio = time.perf_counter()

    bloco = b"x" * (1024 * 1024)

    arquivo = tempfile.NamedTemporaryFile(prefix="io_test_", suffix=".tmp", dir="/tmp", delete=False)

    caminho = arquivo.name

    try:
        # Escrita
        for _ in range(mb):
            arquivo.write(bloco)

        arquivo.flush()

        # Solicita que os dados sejam sincronizados com o armazenamento.
        os.fsync(arquivo.fileno())

        arquivo.close()

        # Leitura
        bytes_lidos = 0

        with open(caminho, "rb") as f:
            while True:
                dados = f.read(1024 * 1024)

                if not dados:
                    break

                bytes_lidos += len(dados)

    finally:
        if not arquivo.closed:
            arquivo.close()

        if os.path.exists(caminho):
            os.remove(caminho)

    tempo_ms = (time.perf_counter() - inicio) * 1000

    return {"escrito_mb": mb, "lido_mb": round(bytes_lidos / 1024 / 1024, 2), "tempo_ms": round(tempo_ms, 2)}
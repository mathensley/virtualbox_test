#!/bin/bash

set -e

APP=${1:-cpu}

case "$APP" in
    cpu)
        MODULO="cpu_app"
        PORTA=8001
        ;;
    memory)
        MODULO="memory_app"
        PORTA=8002
        ;;
    io)
        MODULO="io_app"
        PORTA=8003
        ;;
    *)
        echo "Aplicação inválida: $APP"
        echo ""
        echo "Uso:"
        echo "  ./run.sh cpu"
        echo "  ./run.sh memory"
        echo "  ./run.sh io"
        exit 1
        ;;
esac

# Vai para a pasta onde este script está localizado
cd "$(dirname "$0")"

# Cria o ambiente virtual apenas se ainda não existir
if [ ! -d "venv" ]; then
    echo "Criando ambiente virtual..."
    python3 -m venv venv
fi

# Ativa o ambiente virtual
source venv/bin/activate

# Instala/atualiza as dependências
echo "Instalando dependências..."
pip install -r requirements.txt

echo ""
echo "Iniciando $APP na porta $PORTA..."
echo ""

exec uvicorn "${MODULO}:app" \
    --host 0.0.0.0 \
    --port "$PORTA" \
    --workers 4
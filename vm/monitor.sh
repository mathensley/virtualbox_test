#!/bin/bash

if [ -z "$1" ]; then
    echo "Uso: ./monitor.sh NOME_DO_TESTE [DURACAO]"
    exit 1
fi

TESTE=$1
DURACAO=${2:-65}

DIR="$HOME/resultados/$TESTE"
mkdir -p "$DIR"

echo "Inicio: $(date --iso-8601=seconds)" | tee "$DIR/periodo.txt"

sar -u 1 "$DURACAO" > "$DIR/cpu.txt" &
PID_CPU=$!

sar -r 1 "$DURACAO" > "$DIR/memoria.txt" &
PID_MEM=$!

wait $PID_CPU
wait $PID_MEM

echo "Fim: $(date --iso-8601=seconds)" | tee -a "$DIR/periodo.txt"

echo "Monitoramento finalizado."
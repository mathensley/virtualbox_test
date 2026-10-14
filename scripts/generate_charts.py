from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SUMMARY = ROOT / "results" / "processed" / "summary.csv"
FIG_DIR = ROOT / "results" / "processed" / "figures"

FIG_DIR.mkdir(parents=True, exist_ok=True)


def label_cenario(vcpus: int) -> str:
    return f"{vcpus} vCPU" if vcpus == 1 else f"{vcpus} vCPUs"

def preparar():
    df = pd.read_csv(SUMMARY)
    df = df.sort_values(["vcpus", "usuarios"])
    return df

def grafico_linhas(df, coluna, ylabel, titulo, arquivo):
    fig, ax = plt.subplots(figsize=(8, 5))

    for vcpus, grupo in df.groupby("vcpus"):
        grupo = grupo.sort_values("usuarios")
        ax.plot(
            grupo["usuarios"],
            grupo[coluna],
            marker="o",
            linewidth=2,
            label=label_cenario(int(vcpus)),
        )

    ax.set_title(titulo)
    ax.set_xlabel("Usuários simultâneos (demanda)")
    ax.set_ylabel(ylabel)
    ax.set_xticks(sorted(df["usuarios"].unique()))
    ax.grid(True, alpha=0.3)
    ax.legend(title="Provisionamento")
    fig.tight_layout()
    fig.savefig(FIG_DIR / arquivo, dpi=180)
    plt.close(fig)


def main():
    df = preparar()

    grafico_linhas(
        df,
        "requests_per_s",
        "Requisições por segundo",
        "Vazão por nível de demanda",
        "01_throughput_vs_demand.png",
    )

    grafico_linhas(
        df,
        "response_avg_ms",
        "Tempo médio de resposta (ms)",
        "Latência média por nível de demanda",
        "02_latency_avg_vs_demand.png",
    )

    grafico_linhas(
        df,
        "response_p95_ms",
        "p95 do tempo de resposta (ms)",
        "Latência p95 por nível de demanda",
        "03_latency_p95_vs_demand.png",
    )

    grafico_linhas(
        df,
        "cpu_avg_pct",
        "Utilização média de CPU (%)",
        "Utilização de CPU por nível de demanda",
        "04_cpu_vs_demand.png",
    )

    grafico_linhas(
        df,
        "mem_avg_mb",
        "Memória média utilizada (MB)",
        "Consumo de memória por nível de demanda",
        "05_memory_vs_demand.png",
    )

    print(f"Gráficos salvos em: {FIG_DIR}")


if __name__ == "__main__":
    main()
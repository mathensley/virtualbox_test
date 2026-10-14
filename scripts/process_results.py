from pathlib import Path
from datetime import timedelta
import re

import numpy as np
import pandas as pd

# CONFIGURAÇÃO DO EXPERIMENTO
ROOT = Path(__file__).resolve().parents[1]

RAW_DIR = ROOT / "results" / "raw"
VM_DIR = ROOT / "results" / "vm"
OUTPUT_DIR = ROOT / "results" / "processed"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


CENARIOS = {
    "C1": {"vcpus": 1, "ram_mb": 1024},
    "C2": {"vcpus": 2, "ram_mb": 1024},
    "C3": {"vcpus": 3, "ram_mb": 1024},
    "C4": {"vcpus": 4, "ram_mb": 1024},
}

DEMANDAS = {
    "D1": 1,
    "D2": 2,
    "D3": 4,
    "D4": 8,
}


# PARSERS
def ler_periodo(caminho):
    """
    Lê:
        Inicio: 2026-10-14T16:44:31+00:00
        Fim:    2026-10-14T16:45:36+00:00
    """

    texto = caminho.read_text(encoding="utf-8")

    inicio_match = re.search(r"Inicio:\s*(\S+)", texto)
    fim_match = re.search(r"Fim:\s*(\S+)", texto)

    if not inicio_match or not fim_match:
        raise ValueError(f"Não foi possível ler período de {caminho}")

    inicio = pd.Timestamp(inicio_match.group(1))
    fim = pd.Timestamp(fim_match.group(1))

    return inicio, fim


def criar_timestamp(data_atual, horario, am_pm, timezone):
    """
    Junta a data do periodo.txt com o horário produzido pelo sar.
    """

    timestamp = pd.Timestamp(
        f"{data_atual} {horario} {am_pm}",
        tz=timezone,
    )

    return timestamp


def ler_cpu(caminho, inicio_monitor):
    """
    Converte o cpu.txt produzido por:
        sar -u 1 N

    em um DataFrame.
    """

    linhas = []

    data_atual = inicio_monitor.date()
    anterior = None

    padrao = re.compile(
        r"(\d{2}:\d{2}:\d{2})\s+"
        r"(AM|PM)\s+"
        r"all\s+"
        r"([\d.]+)\s+"   # user
        r"([\d.]+)\s+"   # nice
        r"([\d.]+)\s+"   # system
        r"([\d.]+)\s+"   # iowait
        r"([\d.]+)\s+"   # steal
        r"([\d.]+)"      # idle
    )

    with caminho.open("r", encoding="utf-8", errors="replace") as arquivo:
        for linha in arquivo:
            linha = linha.strip()

            if not linha:
                continue

            if linha.startswith("Linux"):
                continue

            if linha.startswith("Average:"):
                continue

            if "%user" in linha:
                continue

            match = padrao.match(linha)

            if not match:
                continue

            (
                horario,
                am_pm,
                user,
                nice,
                system,
                iowait,
                steal,
                idle,
            ) = match.groups()

            timestamp = criar_timestamp(
                data_atual,
                horario,
                am_pm,
                inicio_monitor.tz,
            )

            # Caso o teste atravesse meia-noite.
            if anterior is not None and timestamp < anterior:
                data_atual += timedelta(days=1)

                timestamp = criar_timestamp(
                    data_atual,
                    horario,
                    am_pm,
                    inicio_monitor.tz,
                )

            anterior = timestamp

            idle = float(idle)

            linhas.append({
                "timestamp": timestamp,
                "cpu_user_pct": float(user),
                "cpu_nice_pct": float(nice),
                "cpu_system_pct": float(system),
                "iowait_pct": float(iowait),
                "steal_pct": float(steal),
                "idle_pct": idle,

                # Uso total da CPU
                "cpu_pct": 100.0 - idle,
            })

    return pd.DataFrame(linhas)


def ler_memoria(caminho, inicio_monitor):
    """
    Converte memoria.txt produzido por:
        sar -r 1 N

    em DataFrame.
    """

    linhas = []

    data_atual = inicio_monitor.date()
    anterior = None

    padrao = re.compile(
        r"(\d{2}:\d{2}:\d{2})\s+"
        r"(AM|PM)\s+"
        r"(.+)"
    )

    with caminho.open("r", encoding="utf-8", errors="replace") as arquivo:
        for linha in arquivo:
            linha = linha.strip()

            if not linha:
                continue

            if linha.startswith("Linux"):
                continue

            if linha.startswith("Average:"):
                continue

            if "kbmemfree" in linha:
                continue

            match = padrao.match(linha)

            if not match:
                continue

            horario, am_pm, restante = match.groups()

            valores = restante.split()

            # Espera-se pelo menos:
            #
            # kbmemfree
            # kbavail
            # kbmemused
            # %memused ...
            if len(valores) < 4:
                continue

            timestamp = criar_timestamp(
                data_atual,
                horario,
                am_pm,
                inicio_monitor.tz,
            )

            if anterior is not None and timestamp < anterior:
                data_atual += timedelta(days=1)

                timestamp = criar_timestamp(
                    data_atual,
                    horario,
                    am_pm,
                    inicio_monitor.tz,
                )

            anterior = timestamp

            kbmemfree = float(valores[0])
            kbavail = float(valores[1])
            kbmemused = float(valores[2])
            memused_pct = float(valores[3])

            linhas.append({
                "timestamp": timestamp,
                "mem_free_mb": kbmemfree / 1024,
                "mem_available_mb": kbavail / 1024,
                "mem_used_mb": kbmemused / 1024,
                "mem_used_pct": memused_pct,
            })

    return pd.DataFrame(linhas)


# PROCESSAMENTO DO LOCUST
def ler_locust(teste):
    stats_path = RAW_DIR / f"{teste}_stats.csv"
    history_path = RAW_DIR / f"{teste}_stats_history.csv"

    if not stats_path.exists():
        raise FileNotFoundError(stats_path)

    if not history_path.exists():
        raise FileNotFoundError(history_path)

    stats = pd.read_csv(stats_path)
    history = pd.read_csv(history_path)

    # Linha Aggregated contém o resumo global do teste.
    aggregated = stats[stats["Name"] == "Aggregated"]

    if aggregated.empty:
        raise ValueError(f"Linha Aggregated não encontrada em {stats_path}")

    aggregated = aggregated.iloc[0]

    # Timestamps do Locust estão em epoch.
    history["timestamp"] = pd.to_datetime(
        history["Timestamp"],
        unit="s",
        utc=True,
    )

    # Pegar apenas o período em que havia usuários ativos.
    ativos = history[
        history["User Count"] > 0
    ].copy()

    if ativos.empty:
        raise ValueError(f"Nenhum usuário ativo encontrado em {history_path}")

    inicio = ativos["timestamp"].min()
    fim = ativos["timestamp"].max()

    return {
        "stats": aggregated,
        "history": ativos,
        "inicio": inicio,
        "fim": fim,
    }


# PROCESSAMENTO DE UM TESTE
def processar_teste(teste):
    print(f"Processando {teste}...")

    match = re.fullmatch(r"(C\d+)_(D\d+)", teste)

    if not match:
        raise ValueError(
            f"Nome de teste inválido: {teste}. "
            f"Esperado algo como C1_D1."
        )

    cenario, demanda = match.groups()

    if cenario not in CENARIOS:
        raise ValueError(f"Cenário desconhecido: {cenario}")

    if demanda not in DEMANDAS:
        raise ValueError(f"Demanda desconhecida: {demanda}")

    # --------------------------------------------------------
    # LOCUST
    # --------------------------------------------------------
    locust = ler_locust(teste)

    stats = locust["stats"]

    inicio_carga = locust["inicio"]
    fim_carga = locust["fim"]

    # --------------------------------------------------------
    # VM
    # --------------------------------------------------------
    vm_dir = VM_DIR / teste

    periodo_path = vm_dir / "periodo.txt"
    cpu_path = vm_dir / "cpu.txt"
    memoria_path = vm_dir / "memoria.txt"

    for caminho in [periodo_path, cpu_path, memoria_path]:
        if not caminho.exists():
            raise FileNotFoundError(caminho)

    inicio_monitor, fim_monitor = ler_periodo(periodo_path)

    cpu = ler_cpu(cpu_path, inicio_monitor)
    memoria = ler_memoria(memoria_path, inicio_monitor)

    # --------------------------------------------------------
    # SINCRONIZAÇÃO
    # --------------------------------------------------------
    # Mantém apenas CPU/RAM coletados enquanto o Locust realmente estava executando usuários.
    cpu_carga = cpu[
        (cpu["timestamp"] >= inicio_carga)
        & (cpu["timestamp"] <= fim_carga)
    ].copy()

    memoria_carga = memoria[
        (memoria["timestamp"] >= inicio_carga)
        & (memoria["timestamp"] <= fim_carga)
    ].copy()

    if cpu_carga.empty:
        raise ValueError(f"Nenhuma amostra de CPU encontrada durante {teste}")

    if memoria_carga.empty:
        raise ValueError(f"Nenhuma amostra de memória encontrada durante {teste}")

    # --------------------------------------------------------
    # MÉTRICAS
    # --------------------------------------------------------
    request_count = int(stats["Request Count"])
    failure_count = int(stats["Failure Count"])

    failure_rate_pct = (
        100 * failure_count / request_count
        if request_count > 0
        else 0
    )

    resultado = {
        # Identificação
        "teste": teste,
        "cenario": cenario,
        "demanda": demanda,

        # Configuração
        "vcpus": CENARIOS[cenario]["vcpus"],
        "ram_mb": CENARIOS[cenario]["ram_mb"],
        "usuarios": DEMANDAS[demanda],

        # Intervalo efetivo
        "inicio_carga": inicio_carga.isoformat(),
        "fim_carga": fim_carga.isoformat(),

        # LOCUST
        "requests": request_count,
        "failures": failure_count,
        "failure_rate_pct": failure_rate_pct,

        "requests_per_s": float(stats["Requests/s"]),

        "response_avg_ms": float(
            stats["Average Response Time"]
        ),

        "response_median_ms": float(
            stats["Median Response Time"]
        ),

        "response_min_ms": float(
            stats["Min Response Time"]
        ),

        "response_max_ms": float(
            stats["Max Response Time"]
        ),

        "response_p95_ms": float(stats["95%"]),
        "response_p99_ms": float(stats["99%"]),

        # CPU
        "cpu_avg_pct": cpu_carga["cpu_pct"].mean(),
        "cpu_max_pct": cpu_carga["cpu_pct"].max(),

        "cpu_p95_pct": np.percentile(
            cpu_carga["cpu_pct"],
            95,
        ),

        "cpu_user_avg_pct": cpu_carga[
            "cpu_user_pct"
        ].mean(),

        "cpu_system_avg_pct": cpu_carga[
            "cpu_system_pct"
        ].mean(),

        "iowait_avg_pct": cpu_carga[
            "iowait_pct"
        ].mean(),

        "steal_avg_pct": cpu_carga[
            "steal_pct"
        ].mean(),

        # MEMÓRIA
        "mem_avg_mb": memoria_carga[
            "mem_used_mb"
        ].mean(),

        "mem_max_mb": memoria_carga[
            "mem_used_mb"
        ].max(),

        "mem_avg_pct": memoria_carga[
            "mem_used_pct"
        ].mean(),

        "mem_max_pct": memoria_carga[
            "mem_used_pct"
        ].max(),
    }

    # --------------------------------------------------------
    # TIMESERIES
    # --------------------------------------------------------
    history = locust["history"].copy()

    history = history.rename(columns={
        "User Count": "users",
        "Requests/s": "locust_rps",
        "Failures/s": "locust_failures_s",
        "Total Average Response Time":
            "locust_avg_response_ms",
    })

    history = history[
        [
            "timestamp",
            "users",
            "locust_rps",
            "locust_failures_s",
            "locust_avg_response_ms",
        ]
    ]

    serie = history.merge(
        cpu_carga[
            [
                "timestamp",
                "cpu_pct",
                "cpu_user_pct",
                "cpu_system_pct",
                "iowait_pct",
            ]
        ],
        on="timestamp",
        how="left",
    )

    serie = serie.merge(
        memoria_carga[
            [
                "timestamp",
                "mem_used_mb",
                "mem_used_pct",
            ]
        ],
        on="timestamp",
        how="left",
    )

    serie.insert(0, "teste", teste)

    return resultado, serie



def main():
    arquivos_stats = sorted(RAW_DIR.glob("*_stats.csv"))

    if not arquivos_stats:
        raise RuntimeError(f"Nenhum arquivo *_stats.csv encontrado em {RAW_DIR}")

    resultados = []
    series = []

    for arquivo in arquivos_stats:
        teste = arquivo.name.removesuffix("_stats.csv")

        resultado, serie = processar_teste(teste)

        resultados.append(resultado)
        series.append(serie)

    # SUMMARY
    summary = pd.DataFrame(resultados)

    summary = summary.sort_values(["vcpus", "usuarios"])

    summary.to_csv(OUTPUT_DIR / "summary.csv", index=False)

    # TIMESERIES
    timeseries = pd.concat(series, ignore_index=True)

    timeseries.to_csv(OUTPUT_DIR / "timeseries.csv", index=False)

    # EXIBIÇÃO
    colunas_principais = [
        "teste",
        "vcpus",
        "usuarios",
        "requests_per_s",
        "response_avg_ms",
        "response_p95_ms",
        "cpu_avg_pct",
        "cpu_max_pct",
        "mem_avg_mb",
        "failures",
    ]

    print("\nRESUMO:")
    print(summary[colunas_principais].round(2).to_string(index=False))
    print(f"Resumo salvo em: {OUTPUT_DIR / 'summary.csv'}")
    print(f"Séries temporais salvas em: {OUTPUT_DIR / 'timeseries.csv'}")


if __name__ == "__main__":
    main()
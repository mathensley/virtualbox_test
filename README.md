# VirtualBox - Demanda, Provisionamento e Desempenho

Este repositório tem o objetivo de estudar a relação entre **demanda**, **provisionamento de recursos**, **desempenho da aplicação** e **utilização da infraestrutura**.

Há três pequenas aplicações web, apenas backend, cada uma com um perfil computacional diferente:

- **CPU-bound**: realiza cálculo de números primos;
- **Memory-bound**: aloca e mantém regiões de memória durante a execução;
- **I/O-bound**: realiza escrita, sincronização e leitura de arquivos temporários.

Para os experimentos de stress foi utilizada a aplicação **CPU-bound**, executada dentro de uma máquina virtual Ubuntu no VirtualBox. A carga é gerada externamente pelo **host**, utilizando o Locust.

Os diretórios de resultados são esses:

- `results/raw/`: arquivos CSV gerados pelo Locust;
- `results/vm/`: arquivos de monitoramento coletados dentro da VM;
- `results/processed/`: resultados consolidados, tabelas e gráficos.

---

# Ambiente utilizado

## Host

O **host** é a máquina física que executa o VirtualBox.

Para execução do primeiro experimento realizado:

```text
Host: Windows 11
Hipervisor: Oracle VirtualBox
```

O Locust e os scripts de processamento dos resultados são executados no host.

## Máquina virtual

A VM utiliza um **arquivo `.vdi` customizado**, com as seguintes configurações:

```text
Sistema operacional: Ubuntu 22.04
Memória base: 1024 MB
Rede: NAT
```

A quantidade de vCPUs é alterada durante os experimentos.

Os cenários utilizados foram:

| Cenário | vCPUs | RAM |
|---|---:|---:|
| C1 | 1 | 1024 MB |
| C2 | 2 | 1024 MB |
| C3 | 3 | 1024 MB |
| C4 | 4 | 1024 MB |

> **Observação:** o `.vdi` não é versionado no Git, principalmente devido ao seu tamanho. Ele deve ser obtido separadamente e mantido em um diretório local permanente.

---

# 1. Configuração da VM no VirtualBox

## 1.1 Criar a máquina virtual

No VirtualBox, deve-se criar uma nova máquina virtual utilizando o `.vdi` fornecido como disco existente.

Configuração inicial:

```text
Tipo: Linux
Sistema: Ubuntu 22.04 64-bit
RAM: 1024 MB
CPU: 1 vCPU
Disco: arquivo .vdi fornecido
Rede: NAT
```

## 1.2 Configurar encaminhamento de portas

Com a VM desligada:

```text
VirtualBox
→ Configurações
→ Rede
→ Adaptador 1
→ NAT
→ Avançado
→ Encaminhamento de Portas
```

Configuração:

| Nome | Protocolo | IP Host | Porta Host | Porta Guest |
|---|---|---|---:|---:|
| SSH | TCP | 127.0.0.1 | 2222 | 22 |
| CPU | TCP | 127.0.0.1 | 8001 | 8001 |
| MEMORY | TCP | 127.0.0.1 | 8002 | 8002 |
| IO | TCP | 127.0.0.1 | 8003 | 8003 |

O IP do guest permanece em branco.

---

# 2. Preparação da VM

Inicia a VM e instala os pacotes necessários:

```bash
sudo apt update

sudo apt install -y \
    python3 \
    python3-pip \
    python3-venv \
    openssh-server \
    sysstat
```

Para ativar o SSH:

```bash
sudo systemctl enable --now ssh
```

E então por fim criar os diretórios utilizados:

```bash
mkdir -p ~/atividade2
mkdir -p ~/resultados
```

---

# 3. Envio das aplicações para a VM

Para copiar os arquivos para a VM:

```powershell
scp -P 2222 `
    apps\cpu_app.py `
    apps\memory_app.py `
    apps\io_app.py `
    vm\requirements.txt `
    vm\run.sh `
    vm\monitor.sh `
    osboxes@localhost:/home/osboxes/atividade2/
```

Depois acessar por SSH:

```powershell
ssh -p 2222 osboxes@localhost
```

Dentro da VM:

```bash
cd atividade2

chmod +x run.sh
chmod +x monitor.sh
```
---

# 4. Executando as aplicações dentro da VM

Todas as aplicações são iniciadas pelo script `run.sh`.

## CPU-bound

Na VM:

```bash
cd ~/atividade2
./run.sh cpu
```

No host Windows:

```powershell
curl.exe http://localhost:8001/health
```

ou:

```powershell
curl.exe "http://localhost:8001/cpu?n=100000"
```

## Memory-bound

Na VM:

```bash
./run.sh memory
```

No host:

```powershell
curl.exe "http://localhost:8002/memory?mb=50&hold_ms=1000"
```

## I/O-bound

Na VM:

```bash
./run.sh io
```

No host:

```powershell
curl.exe "http://localhost:8003/io?mb=20"
```
---

# 5. Metodologia dos testes

Os testes são executados no **host**.

```powershell
pip install locust pandas numpy matplotlib
```

A aplicação utilizada nos testes de provisionamento é a **CPU-bound**.

O endpoint utilizado é:

```text
GET /cpu?n=100000
```

O valor `n=100000` foi mantido fixo em todos os experimentos.

O Locust utiliza um intervalo de espera de `0,5 s` entre as requisições de cada usuário.

Foram utilizados os seguintes níveis de demanda:

| Demanda | Usuários simultâneos |
|---|---:|
| D1 | 1 |
| D2 | 2 |
| D3 | 4 |
| D4 | 8 |

Combinando os quatro cenários de provisionamento com os quatro níveis de demanda temos `16 testes`. Cada teste de carga possui duração de `60 segundos`, o monitoramento da VM é executado por `65 segundos` para garantir que todo o período do Locust esteja coberto.

---

# 6. Executando um experimento

## 6.1 Configurar o provisionamento

Desligue completamente a VM. No VirtualBox:

```text
Configurações
→ Sistema
→ Processador
```

Escolha a quantidade de vCPUs correspondente ao cenário:

```text
C1 = 1 vCPU
C2 = 2 vCPUs
C3 = 3 vCPUs
C4 = 4 vCPUs
```

Mantenha:

```text
RAM = 1024 MB
```

Depois inicie novamente a VM e execute a aplicação. A aplicação é executada com **quatro workers Uvicorn em todos os cenários**, mantendo a configuração da aplicação constante enquanto o número de vCPUs da VM é alterado.

## 6.2 Iniciar o monitoramento da VM

Por outro terminal (pode ser via SSH), execute o script de monitoramento.

Por exemplo, para o teste `C1_D1`:

```bash
./monitor.sh C1_D1 65
```

O script registra CPU, memória e período de monitoramento em:

```text
~/resultados/C1_D1/
```

## 6.3 Locust

Logo após iniciar o monitoramento, execute o Locust no host.

Ainda no exemplo de `C1_D1`:

```powershell
locust -f load_test\locustfile.py `
    --headless `
    --host http://127.0.0.1:8001 `
    -u 1 `
    -r 10 `
    -t 60s `
    --csv results\raw\C1_D1
```

Para os outros níveis de demanda, altere `-u`:

```text
D1 → -u 1
D2 → -u 2
D3 → -u 4
D4 → -u 8
```

Exemplo para `C1_D4`:

```powershell
locust -f load_test\locustfile.py `
    --headless `
    --host http://127.0.0.1:8001 `
    -u 8 `
    -r 10 `
    -t 60s `
    --csv results\raw\C1_D4
```

E só repetir o procedimento para todos os cenários.

Após concluir os experimentos, copie os resultados para o host (pode ser via SCP).

---

# 7. Processamento dos resultados

No host, a partir da raiz do repositório:

```powershell
python scripts/process_results.py
```

O script consolida os arquivos do Locust e do `sar`, sincronizando os timestamps para considerar apenas o intervalo efetivo em que a carga estava ativa.

Os arquivos gerados são:

```text
results/processed/summary.csv
results/processed/timeseries.csv
```

---

# 8. Geração dos gráficos

Execute:

```powershell
python scripts/generate_charts.py
```

Os gráficos são armazenados em:

```text
results/processed/figures/
```
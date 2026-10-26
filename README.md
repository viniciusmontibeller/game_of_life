# Simulação paralela de autômatos celulares — guia de reprodução

Projeto de simulação do Jogo da Vida com regras por posição. Esta documentação apresenta **como compilar, executar e reproduzir as medições**, localmente ou no supercomputador Santos Dumont. A discussão das estratégias OpenMP e dos resultados está no relatório do trabalho.

Trabalho desenvolvido para a disciplina INE5645 — Programação Paralela e Distribuída, da Universidade Federal de Santa Catarina (UFSC), semestre 2026/2.

### Integrantes

- Victor Hugo Fernandes Martins
- Vinicius da Silva Montibeller

### Relatório

O relatório técnico, elaborado segundo o modelo da Sociedade Brasileira de Computação (SBC), encontra-se em:

[relatorio/jogo_da_vida_openmp.pdf](relatorio/jogo_da_vida_openmp.pdf)

O documento apresenta as estratégias de paralelização, a metodologia experimental, os resultados de speedup e eficiência e as conclusões do trabalho.

## 1. Arquivos do projeto

```text
game_of_life/
├── README.md
├── Makefile
│
├── life.c
├── life_parallel_simple.c
├── life_parallel.c
│
├── benchmark.py
├── benchmark_cluster.sh
├── job_benchmark.srm
├── generate_summary.py
├── generate_summary_awk.sh
│
├── ins_outs/
│   ├── life-1.in
│   ├── life-1.out
│   ├── ...
│   └── life-7.in
│
├── relatorio/
│   └── jogo_da_vida_openmp.pdf
│
├── results/                  # criada/utilizada para armazenar os CSVs
└── results_cluster/          # criada/utilizada para armazenar os CSVs de resultados executados no cluster
```

As três versões leem a entrada por `stdin` e escrevem a matriz final em `stdout`. As versões paralelas recebem a quantidade de threads como argumento; a sequencial não recebe esse argumento.

## 2. Execução local

**Requisitos:** Linux ou WSL, GCC com suporte a OpenMP e `make`. Python 3 é necessário **somente** para executar `benchmark.py` e `generate_summary.py`; a compilação e a execução individual não dependem dele.

Na raiz do projeto, compile:

```bash
make
```

O projeto utiliza GCC com otimização `-O3` e `-fopenmp` para as versões paralelas. Os executáveis gerados são `life`, `life_parallel_simple` e `life_parallel`.

### Executar uma entrada individualmente

```bash
./life < ins_outs/life-7.in
./life_parallel_simple 8 < ins_outs/life-7.in
./life_parallel 8 < ins_outs/life-7.in
```

Para salvar uma saída ou comparar com a versão sequencial:

```bash
./life < ins_outs/life-7.in > sequencial.out
./life_parallel 8 < ins_outs/life-7.in > paralelo.out
cmp sequencial.out paralelo.out
```

`cmp` não mostra texto quando as saídas são idênticas.

### Executar o benchmark local com Python

```bash
# Todas as entradas, 10 repetições por configuração
python3 benchmark.py --all --threads 1 2 4 8 16 32 --repetitions 10

# Uma entrada específica
python3 benchmark.py ins_outs/life-7.in --threads 2 4 8 16 --repetitions 10

# Ajuda com as opções disponíveis
python3 benchmark.py --help
```

O benchmark executa e compara as três versões, registra o tempo total de cada execução e grava em `results/` dois arquivos CSV: `*_raw.csv` (medições individuais) e `*_summary.csv` (resumo por entrada, versão e número de threads).

### Execução local sem Python

Os executáveis C podem ser usados normalmente. Para medir uma configuração manualmente com o temporizador do Bash:

```bash
TIMEFORMAT='%6R'
time ./life_parallel 8 < ins_outs/life-7.in > /dev/null
```

Para **reproduzir o benchmark completo sem Python**, utilize o script Bash descrito na seção 3, em um ambiente Linux/WSL com Bash, passando pelas etapas de preparação dos executáveis e de execução do script. O arquivo bruto gerado por esse script pode ser resumido com `generate_summary_awk.sh` (seção 4).

## 3. Execução no supercomputador Santos Dumont (LNCC)

**Requisitos:** conta com acesso ao Santos Dumont, SSH/SCP, compilador GCC, Bash e acesso ao Slurm. Não é necessário Python no cluster. O exemplo pressupõe que o projeto está na pasta `game_of_life/` do computador local.

### 3.1 Enviar os arquivos ao cluster

No computador local, a partir da pasta do projeto, substitua `USUARIO` pelo usuário no Santos Dumont:

```bash
ssh USUARIO@login.sdumont.lncc.br 'mkdir -p ~/game_of_life'
scp life.c life_parallel_simple.c life_parallel.c Makefile \
    benchmark_cluster.sh job_benchmark.srm \
    USUARIO@login.sdumont.lncc.br:~/game_of_life/
scp -r ins_outs USUARIO@login.sdumont.lncc.br:~/game_of_life/
```

Se o cliente SSH exigir, utilize a opção `-o MACs=hmac-sha2-256` no `scp` e `-m hmac-sha2-256` no `ssh`.

### 3.2 Compilar na HOME e preparar a SCRATCH

Após conectar ao cluster:

```bash
cd ~/game_of_life
module load intel_psxe/2020_sequana
make

mkdir -p "$SCRATCH/game_of_life"
cp life life_parallel_simple life_parallel \
    benchmark_cluster.sh job_benchmark.srm \
    "$SCRATCH/game_of_life/"
cp -r ins_outs "$SCRATCH/game_of_life/"
cd "$SCRATCH/game_of_life"
```

Os arquivos são compilados na HOME e os experimentos são executados na SCRATCH, por meio dos nós computacionais disponibilizados pelo Slurm.

### 3.3 Submeter os testes ao Slurm

```bash
sbatch job_benchmark.srm
```

O comando retorna um identificador numérico para o job. Para acompanhar e consultar o resultado, substitua `JOB_ID` pelo identificador recebido:

```bash
squeue -u "$USER"
sacct -j JOB_ID --format=JobID,State,Elapsed,ExitCode
cat life_JOB_ID.out
cat life_JOB_ID.err
ls -lt results/
```

O arquivo `job_benchmark.srm` define os recursos e inicia `benchmark_cluster.sh`. O benchmark usa as entradas `ins_outs/*.in`, testa as versões sequencial, simples e otimizada, valida as saídas e executa repetições com as quantidades de threads definidas no próprio script. Os resultados são salvos como:

```text
results/AAAAMMDD_HHMMSS_cluster_raw.csv
```

O script do cluster gera o **CSV bruto**; o resumo é produzido separadamente, conforme a seção 4. O tempo `Elapsed` mostrado pelo Slurm é o tempo de todo o job e não deve ser usado como tempo de execução de uma configuração.

## 4. Gerar e analisar os resultados

O mesmo procedimento de resumo pode ser utilizado com qualquer arquivo `*_raw.csv` produzido pelo benchmark do cluster. Não é necessário repetir as simulações para gerar o resumo.

### 4.1 Copiar os resultados do cluster

No terminal do cluster, obtenha o diretório de armazenamento:

```bash
echo "$SCRATCH"
```

Em outro terminal, **no computador local**, copie o CSV substituindo `USUARIO`, `CAMINHO_DA_SCRATCH` e o nome do arquivo pelo valor real:

```bash
mkdir -p results
scp USUARIO@login.sdumont.lncc.br:/CAMINHO_DA_SCRATCH/game_of_life/results/AAAAMMDD_HHMMSS_cluster_raw.csv ./results/
```

### 4.2 Com Python 3

```bash
python3 generate_summary.py results/AAAAMMDD_HHMMSS_cluster_raw.csv
```

O script gera `results/AAAAMMDD_HHMMSS_cluster_summary.csv`.

### 4.3 Sem Python: Bash + AWK

A entrega também inclui `generate_summary_awk.sh`, que utiliza ferramentas padrão disponíveis em muitos ambientes Linux/WSL e **não depende de Python**. Pode ser executado localmente ou diretamente na SCRATCH após a conclusão do job (desde que o script esteja no mesmo ambiente):

```bash
sh generate_summary_awk.sh results/AAAAMMDD_HHMMSS_cluster_raw.csv
```

Para escolher explicitamente o nome do resumo:

```bash
sh generate_summary_awk.sh results/AAAAMMDD_HHMMSS_cluster_raw.csv results/resumo.csv
```

**No cluster**, se desejar gerar o resumo antes de transferir os dados, envie o script auxiliar para `~/game_of_life/` por `scp` e copie-o para `"$SCRATCH/game_of_life/"`. Em seguida, execute o comando acima dentro da pasta do projeto na SCRATCH.

### 4.4 Estrutura e interpretação dos CSVs

O CSV bruto (`*_raw.csv`) contém as colunas:

| Coluna | Significado |
|---|---|
| `input` | Arquivo de entrada |
| `version` | `seq`, `simple` ou `optimized` |
| `threads` | Quantidade de threads |
| `repetition` | Número da repetição |
| `time_seconds` | Tempo total medido, em segundos |

O resumo (`*_summary.csv`) agrupa por **entrada, versão e threads**:

| Coluna | Significado |
|---|---|
| `samples` | Número de medições |
| `mean_seconds` | Média dos tempos |
| `median_seconds` | Mediana dos tempos |
| `speedup` | Mediana sequencial ÷ mediana da configuração |
| `efficiency_percent` | `(speedup / threads) × 100` |

As métricas de speedup e eficiência usam como referência a **versão sequencial para a mesma entrada**. Quando a mediana de uma configuração é zero, essas métricas ficam vazias para evitar divisão por zero. Tanto o CSV bruto quanto o de resumo podem ser abertos em planilhas como Excel ou LibreOffice Calc para organizar tabelas e gerar gráficos.

---

A documentação metodológica, os experimentos realizados e a discussão dos resultados estão apresentados no **relatório do trabalho**.

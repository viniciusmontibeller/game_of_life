# Simulação paralela de autômatos celulares — guia de execução

Este projeto possui três implementações da simulação:

| Código-fonte | Executável esperado | Função |
|---|---|---|
| `life.c` | `life` | Referência sequencial original |
| `life_parallel_simple.c` | `life_parallel_simple` | Versão paralela básica, para comparação |
| `life_parallel.c` | `life_parallel` | Versão paralela em desenvolvimento/otimização |

O `benchmark.py` valida os resultados das versões paralelas em relação ao sequencial e mede o **tempo total decorrido** de cada executável, gerando relatórios CSV.

## Requisitos e compilação

- Ambiente Linux (incluindo WSL) com Python 3 e compilador C com suporte a OpenMP, como GCC.
- Os três executáveis precisam estar na mesma pasta que `benchmark.py` e ter os nomes mostrados na tabela.
- A pasta `ins_outs/` contém os arquivos `.in` e, quando disponíveis, os respectivos `.out`.

Se o `Makefile` do projeto compila os três executáveis, execute:

```bash
make
```

Como alternativa, uma compilação com GCC seria:

```bash
gcc -O3 -Wall -Wextra life.c -o life
gcc -O3 -Wall -Wextra -fopenmp life_parallel_simple.c -o life_parallel_simple
gcc -O3 -Wall -Wextra -fopenmp life_parallel.c -o life_parallel
```

> Verifique se o `Makefile` existente já possui esses alvos e flags. Não altere as flags entre versões durante a mesma comparação sem registrar essa diferença.

## Execução individual

Os programas recebem a matriz pela entrada padrão (`stdin`) e imprimem a grade final na saída padrão (`stdout`). **As versões paralelas recebem o número de threads como primeiro argumento**; a versão sequencial não recebe esse argumento.

```bash
# Sequencial
./life < ins_outs/life-1.in

# Paralela simples com 4 threads
./life_parallel_simple 4 < ins_outs/life-1.in

# Paralela otimizada com 8 threads
./life_parallel 8 < ins_outs/life-1.in
```

Para medir rapidamente o tempo total sem exibir a matriz no terminal:

```bash
time ./life < ins_outs/life-1.in > /dev/null
time ./life_parallel_simple 4 < ins_outs/life-1.in > /dev/null
time ./life_parallel 8 < ins_outs/life-1.in > /dev/null
```

No retorno de `time`, **`real`** é o tempo de parede utilizado para comparação. `user` e `sys` são tempos de CPU e não devem substituir `real` no cálculo do speedup.

Para conferir manualmente uma saída:

```bash
./life_parallel 4 < ins_outs/life-1.in > resultado.out
diff -u ins_outs/life-1.out resultado.out
```

Se o `diff` não imprimir diferenças, as saídas são idênticas. A comparação inclui os espaços da matriz.

## Uso do benchmark

Execute o script na raiz do projeto (a pasta onde estão o script e os executáveis):

```bash
python3 benchmark.py ins_outs/life-1.in
```

### Argumentos e opções

| Argumento | Descrição | Padrão |
|---|---|---|
| `ins_outs/life-1.in` | Caminho de um único arquivo de entrada (`.in`). | Obrigatório se não usar `--all` |
| `--all` | Executa todos os arquivos `.in` de `ins_outs/` em uma única rodada. | Desativado |
| `--expected CAMINHO` | Define um `.out` para validar a execução sequencial; apenas com entrada individual. | Procura um `.out` de mesmo nome-base ao lado do `.in` |
| `--threads N [N ...]` | Lista das quantidades de threads para as duas versões paralelas. | `1 2 4 8 16 32` |
| `--repetitions N` | Número de medições de cada configuração por entrada. | `10` |
| `--output PREFIXO` | Escolhe um prefixo para **novos** arquivos CSV. | Nome automático |
| `--append PREFIXO` | Acrescenta medições a arquivos **já existentes**, recalculando o resumo. | Desativado |
| `-h` ou `--help` | Mostra a ajuda do script. | — |

**Restrições:** use um caminho de entrada **ou** `--all`, nunca ambos. `--expected` não pode ser usado com `--all`. `--output` e `--append` são mutuamente exclusivos. Threads e repetições devem ser inteiros positivos.

### Exemplos

```bash
# Uma entrada, usando os valores padrão
python3 benchmark.py ins_outs/life-1.in

# Uma entrada, selecionando threads e número de repetições
python3 benchmark.py ins_outs/life-2.in --threads 1 2 4 8 --repetitions 5

# Usando um arquivo de saída esperado explícito
python3 benchmark.py ins_outs/life-1.in --expected ins_outs/life-1.out

# Todas as entradas da pasta, consolidadas em apenas dois CSVs
python3 benchmark.py --all --threads 1 2 4 8 --repetitions 10

# Criando dois arquivos com prefixo definido pelo usuário
python3 benchmark.py --all --threads 1 2 4 8 --output experimento_01

# Adicionando cinco medições por configuração a um experimento existente
python3 benchmark.py --all --threads 1 2 4 8 --repetitions 5 --append experimento_01

# Consultar a ajuda
python3 benchmark.py --help
```

### Nome dos resultados

Sem `--output`, o script gera automaticamente um prefixo na forma:

```text
AAAAMMDD_<entrada-ou-all>_t<threads>
```

Por exemplo, para uma entrada (`life-1.in`) com 2, 4 e 8 threads:

```text
results/
├── 20261024_life-1_t1-2-4-8_raw.csv
└── 20261024_life-1_t1-2-4-8_summary.csv
```

Com `--all`, a etiqueta `life-1` é substituída por `all`. **Mesmo executando quatro entradas, o benchmark gera somente dois arquivos CSV**: um bruto e um resumo. A coluna `input` identifica a entrada de cada linha.

Com `--output experimento_01`, os nomes serão `experimento_01_raw.csv` e `experimento_01_summary.csv`. O prefixo deve ser apenas um nome, sem barras nem diretórios. Por padrão, arquivos já existentes **não são sobrescritos**; o script informa conflito caso o nome seja reutilizado.

> Todos os arquivos CSV produzidos pelo benchmark são armazenados automaticamente no diretório `results/`, localizado na raiz do projeto. O argumento `--output` recebe apenas o prefixo dos arquivos, sem necessidade de informar o diretório.

### Validação e medição

Para cada entrada, o benchmark:

1. Executa o sequencial e captura sua saída como referência; se houver `.out`, também o verifica.
2. Executa cada versão paralela com as quantidades de threads escolhidas e compara a saída com o sequencial.
3. Faz uma execução de aquecimento de cada configuração, sem registrar tempo.
4. Executa as medições repetidas e mostra cada tempo no terminal.
5. Salva os tempos individuais e calcula um resumo estatístico.

**A validação acontece antes das medições.** Durante os testes cronometrados, as saídas são descartadas (`/dev/null`), e nenhuma comparação de conteúdo é incluída no tempo. O tempo medido pelo Python com `time.perf_counter()` é o **tempo total do processo**, incluindo inicialização, leitura, cálculo e impressão direcionada ao dispositivo de descarte.

O sequencial sempre executa com uma configuração lógica de uma thread. Para cada arquivo `.in`, a quantidade de medições registrada é:

```text
repetitions × (1 + 2 × quantidade_de_valores_em_--threads)
```

Por exemplo, com quatro valores de threads e 10 repetições: `10 × (1 + 2 × 4) = 90` medições por entrada (sem contar validação e aquecimento).

### CSVs e métricas

**`*_raw.csv`** contém uma linha por medição, com:

- `input`: entrada testada;
- `version`: `seq`, `simple` ou `optimized`;
- `threads`: quantidade de threads;
- `repetition`: número da repetição na rodada atual;
- `time_seconds`: tempo medido em segundos.

**`*_summary.csv`** agrega por `input`, `version` e `threads`, com:

- `samples`: número de medições agrupadas;
- `mean_seconds`: média dos tempos;
- `median_seconds`: mediana;
- `speedup`: mediana do sequencial dividida pela mediana da configuração;
- `efficiency_percent`: `speedup / threads × 100`.

O speedup e a eficiência são calculados em relação ao **sequencial original**, não à versão paralela com uma thread. Assim, a eficiência apresentada é relativa à implementação de referência e pode refletir também otimizações sequenciais.

### Continuar uma medição existente com `--append`

Para acrescentar dados a um experimento já criado:

```bash
python3 benchmark.py --all --threads 2 4 8 --repetitions 5 --append experimento_01
```

Informe **somente o prefixo**, sem `_raw`, `_summary` ou `.csv`.

O script exige que ambos os CSVs existam, acrescenta as novas linhas ao `*_raw.csv` e **reescreve o `*_summary.csv` calculando tudo a partir do histórico bruto completo**. As repetições do novo lote recomeçam em 1; é normal haver números de repetição iguais em lotes distintos.

> Atenção: o script não registra a versão do código, o processador ou a configuração de compilação no CSV. Use `--append` apenas quando os resultados forem comparáveis (mesmos executáveis/algoritmos, ambiente e condições relevantes). Para alterações na otimização, prefira um novo prefixo.

## Boas práticas para a comparação

- Use as mesmas entradas e condições de compilação para todas as versões.
- Faça várias repetições e dê atenção à mediana e à dispersão, além da média.
- Compare a mesma quantidade de threads nas duas versões paralelas.
- Não extrapole o número de threads além dos recursos computacionais alocados.
- No supercomputador, execute as medições em nós computacionais alocados pelo sistema de filas, evitando o nó de login.
- Registre externamente a máquina, o compilador, as flags, o número de núcleos e a revisão do código para permitir reprodução dos experimentos.
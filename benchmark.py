import argparse
import csv
import statistics
import subprocess
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
INPUT_DIR = ROOT / 'ins_outs'
RESULTS_DIR = ROOT / 'results'
VERSIONS = {
    'seq': ROOT / 'life',
    'simple': ROOT / 'life_parallel_simple',
    'optimized': ROOT / 'life_parallel',
}
DEFAULT_THREADS = [1, 2, 4, 8, 16, 32]
RAW_COLUMNS = ['input', 'version', 'threads', 'repetition', 'time_seconds']
SUMMARY_COLUMNS = [
    'input', 'version', 'threads', 'samples', 'mean_seconds',
    'median_seconds', 'speedup', 'efficiency_percent',
]


def get_command(version, threads):
    executable = str(VERSIONS[version])
    return [executable] if version == 'seq' else [executable, str(threads)]


def execute(version, threads, input_file, capture_output=False):
    with input_file.open('rb') as source:
        result = subprocess.run(
            get_command(version, threads),
            stdin=source,
            stdout=subprocess.PIPE if capture_output else subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            check=True,
        )
    return result.stdout


def validate(input_file, expected_file, thread_counts):
    print(f'\nValidando: {input_file.name}', flush=True)
    reference = execute('seq', 1, input_file, capture_output=True)
    if expected_file is not None and reference != expected_file.read_bytes():
        raise RuntimeError(f'Sequencial difere de {expected_file.name}')
    for version in ('simple', 'optimized'):
        for threads in thread_counts:
            actual = execute(version, threads, input_file, capture_output=True)
            if actual != reference:
                raise RuntimeError(
                    f'Saida incorreta: {input_file.name}, {version}, {threads} threads'
                )
            print(f'  OK: {version}, {threads} threads', flush=True)


def measure(version, threads, input_file):
    with input_file.open('rb') as source:
        start = time.perf_counter()
        subprocess.run(
            get_command(version, threads),
            stdin=source,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
        return time.perf_counter() - start


def get_inputs(args):
    if args.all:
        inputs = sorted(INPUT_DIR.glob('*.in'))
        if not inputs:
            raise ValueError(f'Nenhum .in encontrado em {INPUT_DIR}')
        return [(p, p.with_suffix('.out') if p.with_suffix('.out').exists() else None)
                for p in inputs]
    source = Path(args.input)
    if not source.is_file():
        raise FileNotFoundError(source)
    expected = Path(args.expected) if args.expected else source.with_suffix('.out')
    if args.expected and not expected.is_file():
        raise FileNotFoundError(expected)
    return [(source, expected if expected.is_file() else None)]


def read_raw(path):
    with path.open(newline='') as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != RAW_COLUMNS:
            raise ValueError(f'Colunas incompativeis em {path}')
        return list(reader)


def write_csv(path, rows, columns, mode='w'):
    with path.open(mode, newline='') as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        if mode != 'a' or f.tell() == 0:
            writer.writeheader()
        writer.writerows(rows)


def build_summary(raw_rows):
    grouped = defaultdict(list)
    for row in raw_rows:
        key = (row['input'], row['version'], int(row['threads']))
        grouped[key].append(float(row['time_seconds']))

    summary = []
    for (input_name, version, threads), times in sorted(grouped.items()):
        seq_times = grouped.get((input_name, 'seq', 1))
        if not seq_times:
            raise ValueError(f'Sem tempo sequencial para {input_name}')
        median = statistics.median(times)
        reference = statistics.median(seq_times)
        speedup = reference / median
        summary.append({
            'input': input_name,
            'version': version,
            'threads': threads,
            'samples': len(times),
            'mean_seconds': round(statistics.mean(times), 6),
            'median_seconds': round(median, 6),
            'speedup': round(speedup, 4),
            'efficiency_percent': round(speedup / threads * 100, 2),
        })
    return summary


def main():
    parser = argparse.ArgumentParser(description='Benchmark de life (seq, simple e optimized)')
    parser.add_argument('input', nargs='?', help='Arquivo .in individual')
    parser.add_argument('--expected', help='Arquivo .out para validacao (opcional)')
    parser.add_argument('--all', action='store_true', help='Usa todos os .in de ins_outs/')
    parser.add_argument('--output', help='Prefixo para NOVOS CSVs (sem _raw ou _summary)')
    parser.add_argument('--append', metavar='PREFIXO', help='Acrescenta a CSVs EXISTENTES com este prefixo')
    parser.add_argument('--repetitions', type=int, default=10)
    parser.add_argument('--threads', nargs='+', type=int, default=DEFAULT_THREADS)
    args = parser.parse_args()

    if args.all == bool(args.input):
        parser.error('Informe um arquivo de entrada OU --all.')
    if args.all and args.expected:
        parser.error('--expected nao pode ser combinado com --all.')
    if args.output and args.append:
        parser.error('Use --output ou --append PREFIXO, nunca os dois.')
    if args.repetitions < 1 or not args.threads or any(n < 1 for n in args.threads):
        parser.error('Repeticoes e numeros de threads devem ser positivos.')

    threads = sorted(set(args.threads))
    inputs = get_inputs(args)
    if args.append:
        prefix = args.append
    elif args.output:
        prefix = args.output
    else:
        stamp = datetime.now().strftime('%Y%m%d')
        tag = 'all' if args.all else Path(args.input).stem
        thread_tag = '-'.join(map(str, threads))
        prefix = f'{stamp}_{tag}_t{thread_tag}'

    # O prefixo e apenas um nome, nao um caminho para fora de results/.
    if not prefix or prefix in ('.', '..') or Path(prefix).name != prefix or '/' in prefix or '\\' in prefix:
        parser.error('O prefixo deve ser apenas um nome de arquivo, sem pastas.')
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    raw_path = RESULTS_DIR / f'{prefix}_raw.csv'
    summary_path = RESULTS_DIR / f'{prefix}_summary.csv'

    if args.append:
        if not raw_path.is_file() or not summary_path.is_file():
            parser.error('Para --append, os arquivos _raw.csv e _summary.csv devem existir.')
        previous_rows = read_raw(raw_path)
    else:
        if raw_path.exists() or summary_path.exists():
            parser.error('Arquivos ja existem. Use outro --output ou --append PREFIXO.')
        previous_rows = []

    new_rows = []
    for input_file, expected_file in inputs:
        validate(input_file, expected_file, threads)
        configurations = [('seq', 1)]
        for n in threads:
            configurations += [('simple', n), ('optimized', n)]

        # Aquecimento: nao faz parte das medidas.
        for version, n in configurations:
            measure(version, n, input_file)

        for repetition in range(1, args.repetitions + 1):
            ordered = configurations if repetition % 2 else list(reversed(configurations))
            for version, n in ordered:
                elapsed = measure(version, n, input_file)
                new_rows.append({
                    'input': input_file.name,
                    'version': version,
                    'threads': n,
                    'repetition': repetition,
                    'time_seconds': elapsed,
                })
                print(f'{input_file.name} | {version:9} | threads={n:2} | '
                      f'rep={repetition:2} | {elapsed:.6f}s', flush=True)

    # Summary SEMPRE refeito a partir do historico bruto inteiro.
    all_rows = previous_rows + new_rows
    summary = build_summary(all_rows)
    write_csv(raw_path, new_rows, RAW_COLUMNS, mode='a' if args.append else 'x')
    # Reescrita atomica para evitar summary truncado se a escrita falhar.
    temporary = summary_path.with_suffix('.tmp')
    write_csv(temporary, summary, SUMMARY_COLUMNS)
    temporary.replace(summary_path)
    print(f'\nBenchmark concluido. {len(new_rows)} novas medidas; '
          f'{len(all_rows)} no total.')
    print(f'Raw: {raw_path}')
    print(f'Summary: {summary_path}')


if __name__ == '__main__':
    main()

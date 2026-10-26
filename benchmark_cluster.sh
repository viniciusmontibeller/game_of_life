#!/bin/bash
set -euo pipefail

INPUT_DIR="ins_outs"
RESULTS_DIR="results"

THREADS=(2 4 8 16 32)
REPETITIONS=10

mkdir -p "$RESULTS_DIR"

RUN_ID=$(date +%Y%m%d_%H%M%S)
RAW_FILE="$RESULTS_DIR/${RUN_ID}_cluster_raw.csv"

echo "input,version,threads,repetition,time_seconds" > "$RAW_FILE"

# Arquivos temporarios para validacao
REFERENCE=$(mktemp)
OUTPUT=$(mktemp)

trap 'rm -f "$REFERENCE" "$OUTPUT"' EXIT

measure() {
    local input="$1"
    local version="$2"
    local threads="$3"
    local repetition="$4"
    shift 4

    local elapsed

    # Medicao robusta usando arquivo temporario
    local time_file
    time_file=$(mktemp)

    /usr/bin/time -f "%e" -o "$time_file" \
        "$@" < "$input" > /dev/null

    elapsed=$(cat "$time_file")
    rm -f "$time_file"

    echo "$(basename "$input"),$version,$threads,$repetition,$elapsed" \
        >> "$RAW_FILE"

    echo "$input | $version | $threads threads | ${elapsed}s"
}

for input in "$INPUT_DIR"/*.in; do
    name=$(basename "$input")

    echo "Validando $name"

    ./life < "$input" > "$REFERENCE"

    expected="${input%.in}.out"

    if [ -f "$expected" ]; then
        cmp "$REFERENCE" "$expected"
    fi

    for threads in "${THREADS[@]}"; do
        ./life_parallel_simple "$threads" < "$input" > "$OUTPUT"
        cmp "$REFERENCE" "$OUTPUT"

        ./life_parallel "$threads" < "$input" > "$OUTPUT"
        cmp "$REFERENCE" "$OUTPUT"
    done

    echo "Validacao concluida: $name"

    for repetition in $(seq 1 "$REPETITIONS"); do
        measure "$input" seq 1 "$repetition" \
            ./life

        for threads in "${THREADS[@]}"; do
            measure "$input" simple "$threads" "$repetition" \
                ./life_parallel_simple "$threads"

            measure "$input" optimized "$threads" "$repetition" \
                ./life_parallel "$threads"
        done
    done
done

echo "Resultados salvos em $RAW_FILE"
#!/bin/sh
# POSIX awk fallback for cluster raw CSVs, no Python required.
set -eu
if [ "$#" -lt 1 ] || [ "$#" -gt 2 ]; then
  echo "Uso: sh generate_summary_awk.sh arquivo_raw.csv [arquivo_summary.csv]" >&2
  exit 2
fi
raw=$1
if [ "$#" -eq 2 ]; then
  output=$2
else
  case "$raw" in
    *_raw.csv) output="${raw%_raw.csv}_summary.csv" ;;
    *) echo "Informe o arquivo de saida para nomes sem _raw.csv" >&2; exit 2 ;;
  esac
fi
[ -f "$raw" ] || { echo "CSV nao encontrado: $raw" >&2; exit 2; }
[ "$raw" != "$output" ] || { echo "Saida nao pode sobrescrever a entrada" >&2; exit 2; }
LC_ALL=C awk -F, '
function sort_times(key,   i,j,temp,n) {
  n = count[key]
  for (i=2; i<=n; i++) {
    temp = times[key SUBSEP i]
    j=i-1
    while (j>=1 && times[key SUBSEP j] > temp) {
      times[key SUBSEP (j+1)] = times[key SUBSEP j]
      j--
    }
    times[key SUBSEP (j+1)] = temp
  }
  if (n%2) return times[key SUBSEP ((n+1)/2)]
  return (times[key SUBSEP (n/2)] + times[key SUBSEP (n/2+1)])/2
}
BEGIN {OFS=","; print "input,version,threads,samples,mean_seconds,median_seconds,speedup,efficiency_percent"}
NR==1 {if ($1!="input" || $2!="version" || $3!="threads" || $5!="time_seconds") {print "Cabecalho CSV invalido" > "/dev/stderr"; exit 2}; next}
NF<5 {next}
{
  sub(/\r$/, "", $5)
  input=$1; version=$2; threads=$3+0; value=$5+0
  key=input SUBSEP version SUBSEP threads
  if (!(key in count)) {
    order[++num_keys]=key
    inputs[key]=input; versions[key]=version; thread_count[key]=threads
  }
  count[key]++
  times[key SUBSEP count[key]]=value
  total[key]+=value
}
END {
  for (i=1; i<=num_keys; i++) {
    key=order[i]
    median[key]=sort_times(key)
  }
  for (i=1; i<=num_keys; i++) {
    key=order[i]; reference=inputs[key] SUBSEP "seq" SUBSEP 1
    speedup=""; efficiency=""
    if ((reference in count) && median[key]>0) {
      speedup=median[reference]/median[key]
      efficiency=100*speedup/thread_count[key]
    }
    printf "%s,%s,%d,%d,%.6f,%.6f,", inputs[key],versions[key],thread_count[key],count[key],total[key]/count[key],median[key]
    if (speedup!="") printf "%.4f,%.2f\n",speedup,efficiency
    else printf ",\n"
  }
}
' "$raw" > "$output"
echo "Resumo gerado: $output"

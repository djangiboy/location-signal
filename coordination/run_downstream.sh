#!/usr/bin/env bash
# Chains classify -> embed -> aggregate -> merge after transcribe finishes.
# Called manually (or automatically) once transcribe_calls.py is done.
set -e

cd "$(dirname "$0")"

echo "==== 1/4  classify (Haiku, 10 workers) ===="
rm -f investigative/transcripts_classified.csv
python classify_reasons.py --llm-backend claude --workers 10 2>&1 | tail -25

echo ""
echo "==== 2/4  embeddings ===="
python embedding_classify.py 2>&1 | tail -15

echo ""
echo "==== 3/4  aggregate per pair ===="
python aggregate_per_pair.py 2>&1 | tail -20

echo ""
echo "==== 4/4  merge with allocation ===="
python merge_with_allocation.py 2>&1 | grep -v UserWarning | grep -v "pd.read_sql" | grep -E "merged|alloc rows|WROTE" | head -10

echo ""
echo "==== DONE ===="

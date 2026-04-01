#!/bin/bash
# NeuroSummarizer — scheduled article fetching
# Cron example (every 6 hours):
#   0 */6 * * * /root/neurosummarizer/fetch_articles.sh >> /root/neurosummarizer/cron.log 2>&1

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"
source venv/bin/activate

echo ""
echo "=========================================="
echo "  Fetch started: $(date)"
echo "=========================================="

echo "[1/3] Fetching from arXiv..."
python fetch_arxiv.py

echo "[2/3] Fetching from PubMed..."
python fetch_pubmed.py

echo "[3/3] Summarising new articles..."
python summarize_articles.py

echo "=========================================="
echo "  Fetch completed: $(date)"
echo "=========================================="

#!/bin/bash

cd /root/neurosummarizer
source venv/bin/activate

python fetch_arxiv.py
python fetch_pubmed.py
python summarize_articles.py

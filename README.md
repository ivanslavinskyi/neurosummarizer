# NeuroSummarizer 🧠

**NeuroSummarizer** is an inclusive, open-source tool designed to automatically fetch, summarize, and present the latest scientific publications about gliomas and neuroscience.

It is built with Python, FastAPI, and modern frontend principles, aiming to support researchers, clinicians, and students.

## ✨ Features

- 🔍 Fetches articles from **PubMed** and **arXiv**
- 🤖 Summarizes abstracts using OpenAI/GPT
- 📄 Clean web interface with pagination, search, sorting
- 🌒 Light/dark theme switcher
- 📥 Export to **CSV**, **JSON**, and **Weekly PDF Digest**
- 🔐 Prevents duplicate entries
- 🧠 Useful for neurology and oncology researchers

## 🚀 Tech Stack

- **Python 3.10**
- **FastAPI** + **Uvicorn**
- **SQLite** + SQLAlchemy
- **HTML + JS frontend** (vanilla)
- **pdfkit + wkhtmltopdf** for PDF generation

## 📦 Installation

```bash
git clone https://github.com/your-username/neurosummarizer.git
cd neurosummarizer
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

You also need `wkhtmltopdf` installed:

```bash
sudo apt install wkhtmltopdf
```

## 🧪 Run locally

```bash
uvicorn main:app --reload
```

Then open [http://localhost:8000](http://localhost:8000)

## 📄 License

MIT — open to use and contribution.
Maintained by [Ivan Slavinskyi](https://neurosummarizer.online)
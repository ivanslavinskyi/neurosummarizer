# NeuroSummarizer 🧠

**NeuroSummarizer** is a full-featured platform that automatically aggregates, summarizes, and presents the latest scientific publications across multiple neuroscience research domains.

Built with Python, FastAPI, and a modern vanilla JS frontend. Designed for researchers, clinicians, and students working in neuro-oncology, neurodegenerative diseases, neuroimaging, and epilepsy.

🔗 **Live**: [neurosummarizer.online](https://neurosummarizer.online)

---

## ✨ Features

### Multi-Source Article Aggregation
- 🔍 Automated fetching from **PubMed** (NCBI E-Utilities) and **arXiv** API
- 🗂️ **Dynamic category system** — articles are automatically classified into research domains
- 🔐 Duplicate detection (by URL for arXiv, by title+source for PubMed)
- ⏱️ Cron-based scheduling (default: daily at 08:00 UTC)

### AI-Powered Summarization
- 🤖 Abstracts are summarized into 1–2 sentence plain-English summaries using **OpenAI GPT-4o-mini**
- ♻️ Retry logic with configurable delay (3 attempts per article)
- Only articles without existing summaries are processed (idempotent)

### Category Management
- 📁 4 built-in categories: **Glioma Research**, **Neurodegenerative Diseases**, **Brain Imaging / Neuroimaging**, **Epilepsy**
- Each category has configurable comma-separated search queries
- Categories can be created, edited, activated/deactivated, and deleted via admin panel
- Articles are automatically assigned to the correct category during fetching

### Public Web Interface
- 📄 Responsive article feed with pagination, full-text search, and keyword filtering
- 🏷️ Filter by category and data source (arXiv / PubMed)
- 🔀 Sortable by date (ascending/descending)
- 🌗 Light / dark theme switcher
- 📊 About and Contact pages

### Data Export
- 📥 **CSV** — all articles with metadata
- 📥 **JSON** — full article data as JSON array
- 📥 **Weekly PDF Digest** — auto-generated PDF report of articles added in the last 7 days

### Admin Panel (`/admin`)
- 🔑 JWT-based authentication (bcrypt password hashing)
- 📊 Dashboard with statistics: total articles, added today, by source, by category, daily chart (14 days)
- 🗂️ Full CRUD for categories (create, update, delete, toggle active)
- 📝 Article management: delete articles, reassign categories
- 🔒 All admin endpoints protected with Bearer token auth

---

## 🏗️ Architecture

```
neurosummarizer/
├── main.py                 # FastAPI app — all API endpoints + startup logic
├── database.py             # SQLAlchemy models (Article, Category, AdminUser) + migrations
├── auth.py                 # JWT auth + bcrypt password utilities
├── fetch_arxiv.py          # arXiv fetcher — per-category, per-query
├── fetch_pubmed.py         # PubMed fetcher — per-category, per-query  
├── summarize_articles.py   # OpenAI GPT summarization pipeline
├── fetch_articles.sh       # Cron entry point — runs all 3 scripts sequentially
├── init_db.py              # One-time migration & seed script
├── requirements.txt        # Python dependencies
├── .env                    # Environment variables (API keys, credentials)
├── database/
│   └── articles.db         # SQLite database
└── static/
    ├── index.html          # Public article feed
    ├── admin.html          # Admin panel (SPA)
    ├── about.html          # About page
    ├── contact.html        # Contact page
    └── styles.css          # Global styles (light/dark themes)
```

### Data Flow

```
┌──────────────────────────────────────────────────────────┐
│                    Cron (daily 08:00 UTC)                 │
│                   fetch_articles.sh                       │
├──────────────┬──────────────────┬─────────────────────────┤
│ fetch_arxiv  │  fetch_pubmed    │  summarize_articles     │
│   ↓          │     ↓            │      ↓                  │
│ arXiv API    │  NCBI E-Utils    │  OpenAI GPT-4o-mini     │
│ (feedparser) │  (requests+XML)  │  (openai SDK)           │
├──────────────┴──────────────────┴─────────────────────────┤
│                   SQLite (articles.db)                     │
├───────────────────────────────────────────────────────────┤
│              FastAPI (main.py) + Uvicorn                   │
├───────────────────────────────────────────────────────────┤
│           Vanilla JS Frontend (static/*.html)              │
└───────────────────────────────────────────────────────────┘
```

---

## 🚀 Tech Stack

| Layer | Technology |
|---|---|
| Backend | **Python 3.10**, **FastAPI**, **Uvicorn** |
| Database | **SQLite** + **SQLAlchemy** (ORM + migrations) |
| Auth | **JWT** (python-jose) + **bcrypt** |
| AI | **OpenAI GPT-4o-mini** |
| Data Sources | **PubMed** (E-Utilities API), **arXiv** (Atom/RSS) |
| Frontend | Vanilla **HTML/CSS/JS** (no frameworks) |
| PDF | **pdfkit** + **wkhtmltopdf** |
| Templates | **Jinja2** (PDF rendering) |

---

## 📦 Installation

### Prerequisites
- Python 3.10+
- `wkhtmltopdf` (for PDF export)

### Setup

```bash
git clone https://github.com/your-username/neurosummarizer.git
cd neurosummarizer
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
sudo apt install wkhtmltopdf
```

### Environment Variables

Create a `.env` file:

```env
OPENAI_API_KEY=sk-...
ADMIN_USERNAME=admin
ADMIN_PASSWORD=your-secure-password
JWT_SECRET=your-random-secret-key
```

### Initialize Database

```bash
python init_db.py
```

This will:
1. Create/migrate the SQLite database schema
2. Seed default categories (Glioma, Neurodegenerative, Neuroimaging, Epilepsy)
3. Create the admin user
4. Assign uncategorized articles to Glioma

---

## 🧪 Running

### Development

```bash
uvicorn main:app --reload
```

Then open [http://localhost:8000](http://localhost:8000)

### Production

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

### Automated Fetching (Cron)

```bash
chmod +x fetch_articles.sh
crontab -e
```

Add:
```
0 8 * * * /root/neurosummarizer/fetch_articles.sh >> /root/neurosummarizer/fetch_log.txt 2>&1
```

This runs daily at 08:00 UTC and sequentially:
1. Fetches from arXiv (all active categories × all search queries)
2. Fetches from PubMed (same)
3. Summarizes any articles that don't have a summary yet

---

## 🔌 API Reference

### Public Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Homepage |
| `GET` | `/about/` | About page |
| `GET` | `/contact/` | Contact page |
| `GET` | `/health` | Health check |
| `GET` | `/api/articles` | List articles (paginated, searchable, filterable) |
| `GET` | `/api/articles/count-today` | Count of articles added today |
| `GET` | `/api/categories` | List all categories with article counts |
| `GET` | `/api/export/csv` | Export all articles as CSV |
| `GET` | `/api/export/json` | Export all articles as JSON |
| `GET` | `/api/export/weekly-pdf` | Generate weekly digest PDF |

#### Query Parameters for `/api/articles`

| Param | Type | Default | Description |
|---|---|---|---|
| `q` | string | — | Full-text search (title, abstract, summary) |
| `keyword` | string | — | Keyword filter |
| `category_id` | int | — | Filter by category |
| `source` | string | — | Filter by source (`arXiv` / `PubMed`) |
| `limit` | int | 10 | Results per page (1–100) |
| `offset` | int | 0 | Pagination offset |
| `sort_by` | string | `date` | Sort field (`date` or `id`) |
| `order` | string | `desc` | Sort order (`asc` / `desc`) |

### Admin Endpoints (JWT required)

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/admin/login` | Login, returns JWT token |
| `GET` | `/api/admin/categories` | List categories (admin view) |
| `POST` | `/api/admin/categories` | Create category |
| `PUT` | `/api/admin/categories/{id}` | Update category |
| `DELETE` | `/api/admin/categories/{id}` | Delete category |
| `DELETE` | `/api/admin/articles/{id}` | Delete article |
| `PUT` | `/api/admin/articles/{id}/category` | Reassign article category |
| `GET` | `/api/admin/stats` | Dashboard statistics |

---

## 📄 License

MIT — open to use and contribution.

Maintained by [Ivan Slavinskyi](https://neurosummarizer.online)
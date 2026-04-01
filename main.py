"""
NeuroSummarizer — FastAPI application.

Public endpoints:  articles feed, search, categories, export.
Admin  endpoints:  login, CRUD categories, manage articles, stats.
"""

from fastapi import FastAPI, Depends, Query, HTTPException, Body
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta, date
from jinja2 import Template
import pdfkit, csv, io, os

from database import SessionLocal, Article, Category, AdminUser, migrate_db
from auth import (
    hash_password, verify_password, create_token, get_current_admin,
)
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(title="NeuroSummarizer", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://neurosummarizer.online",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Startup — auto-migrate & seed
# ---------------------------------------------------------------------------

@app.on_event("startup")
def on_startup():
    migrate_db()
    _seed_defaults()


def _seed_defaults():
    """Create initial categories and admin user if they don't exist."""
    db = SessionLocal()
    try:
        # Categories
        INITIAL = [
            ("glioma", "Glioma Research",
             "glioma,glioblastoma,GBM,brain tumor,astrocytoma", "#ef4444"),
            ("neurodegenerative", "Neurodegenerative Diseases",
             "neurodegenerative,Alzheimer,Parkinson,ALS,dementia,Huntington", "#8b5cf6"),
            ("neuroimaging", "Brain Imaging / Neuroimaging",
             "neuroimaging,brain imaging,fMRI,MRI brain,PET brain,diffusion tensor", "#3b82f6"),
            ("epilepsy", "Epilepsy",
             "epilepsy,seizure,anticonvulsant,epileptic,antiepileptic", "#10b981"),
        ]
        for name, display, queries, color in INITIAL:
            if not db.query(Category).filter_by(name=name).first():
                db.add(Category(
                    name=name, display_name=display,
                    search_queries=queries, color=color, is_active=True,
                ))

        # Admin user
        uname = os.getenv("ADMIN_USERNAME", "admin")
        if not db.query(AdminUser).filter_by(username=uname).first():
            pwd = os.getenv("ADMIN_PASSWORD", "neuro2026!")
            db.add(AdminUser(username=uname, password_hash=hash_password(pwd)))
            print(f"[startup] Created admin user: {uname}")

        db.commit()

        # Assign un-categorised articles to Glioma
        glioma = db.query(Category).filter_by(name="glioma").first()
        if glioma:
            db.query(Article).filter(
                Article.category_id.is_(None)
            ).update({Article.category_id: glioma.id})
            db.commit()
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Static files & pages
# ---------------------------------------------------------------------------

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def homepage():
    return FileResponse("static/index.html")


@app.get("/about/")
async def about():
    return FileResponse("static/about.html")


@app.get("/contact/")
async def contact():
    return FileResponse("static/contact.html")


@app.get("/admin")
@app.get("/admin/")
async def admin_page():
    return FileResponse("static/admin.html")


@app.get("/health")
async def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class LoginRequest(BaseModel):
    username: str
    password: str


class CategoryCreate(BaseModel):
    name: str
    display_name: str
    search_queries: str = ""
    color: str = "#3b82f6"
    is_active: bool = True


class CategoryUpdate(BaseModel):
    display_name: Optional[str] = None
    search_queries: Optional[str] = None
    color: Optional[str] = None
    is_active: Optional[bool] = None


def _article_dict(a: Article) -> dict:
    """Serialize an Article to a safe dict (no SQLAlchemy internals)."""
    return {
        "id": a.id,
        "title": a.title,
        "authors": a.authors,
        "abstract": a.abstract,
        "summary": a.summary,
        "source": a.source,
        "publication_date": a.publication_date.isoformat() if a.publication_date else None,
        "url": a.url,
        "keywords": a.keywords,
        "date_added": a.date_added.isoformat() if a.date_added else None,
        "category_id": a.category_id,
        "category_name": a.category.display_name if a.category else None,
        "category_color": a.category.color if a.category else None,
    }


def _category_dict(c: Category, count: int = 0) -> dict:
    return {
        "id": c.id,
        "name": c.name,
        "display_name": c.display_name,
        "search_queries": c.search_queries,
        "color": c.color,
        "is_active": c.is_active,
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "article_count": count,
    }


# ---------------------------------------------------------------------------
# PUBLIC  — Articles
# ---------------------------------------------------------------------------

@app.get("/api/articles")
@app.get("/api/articles/")
async def get_articles(
    db: Session = Depends(get_db),
    q: Optional[str] = Query(None, description="Full-text search"),
    keyword: Optional[str] = Query(None),
    category_id: Optional[int] = Query(None),
    source: Optional[str] = Query(None),
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    sort_by: str = Query("date"),
    order: str = Query("desc"),
):
    query = db.query(Article)

    # Full-text search across title, abstract, summary
    if q:
        like = f"%{q}%"
        query = query.filter(or_(
            Article.title.ilike(like),
            Article.abstract.ilike(like),
            Article.summary.ilike(like),
        ))

    # Legacy keyword filter
    if keyword:
        query = query.filter(Article.keywords.ilike(f"%{keyword}%"))

    # Category filter
    if category_id:
        query = query.filter(Article.category_id == category_id)

    # Source filter
    if source:
        query = query.filter(Article.source == source)

    # Sort
    sort_col = Article.publication_date if sort_by == "date" else Article.id
    query = query.order_by(sort_col.asc() if order == "asc" else sort_col.desc())

    total = query.count()
    articles = query.offset(offset).limit(limit).all()

    return {
        "total": total,
        "count": len(articles),
        "offset": offset,
        "limit": limit,
        "results": [_article_dict(a) for a in articles],
    }


@app.get("/api/articles/count-today")
async def count_today(db: Session = Depends(get_db)):
    today = date.today()
    count = db.query(Article).filter(Article.date_added == today).count()
    return {"date": today.isoformat(), "count": count}


# ---------------------------------------------------------------------------
# PUBLIC  — Categories
# ---------------------------------------------------------------------------

@app.get("/api/categories")
@app.get("/api/categories/")
async def get_categories(db: Session = Depends(get_db)):
    cats = db.query(Category).order_by(Category.display_name).all()
    result = []
    for c in cats:
        count = db.query(Article).filter(Article.category_id == c.id).count()
        result.append(_category_dict(c, count))
    return result


# ---------------------------------------------------------------------------
# PUBLIC  — Export
# ---------------------------------------------------------------------------

@app.get("/api/export/csv")
async def export_csv(db: Session = Depends(get_db)):
    articles = db.query(Article).order_by(Article.publication_date.desc()).all()
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["ID", "Title", "Authors", "Source", "Category", "Date", "Summary", "URL"])
    for a in articles:
        writer.writerow([
            a.id, a.title, a.authors, a.source,
            a.category.display_name if a.category else "",
            a.publication_date, a.summary, a.url,
        ])
    buffer.seek(0)
    return StreamingResponse(buffer, media_type="text/csv", headers={
        "Content-Disposition": "attachment; filename=articles.csv"
    })


@app.get("/api/export/json")
async def export_json(db: Session = Depends(get_db)):
    articles = db.query(Article).order_by(Article.publication_date.desc()).all()
    return JSONResponse(content=[_article_dict(a) for a in articles])


@app.get("/api/export/weekly-pdf")
async def export_weekly_pdf(db: Session = Depends(get_db)):
    today = datetime.today().date()
    week_ago = today - timedelta(days=7)
    articles = (
        db.query(Article)
        .filter(Article.date_added >= week_ago)
        .order_by(Article.publication_date.desc())
        .all()
    )

    html_template = """
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body { font-family: Arial, sans-serif; padding: 40px; }
            h1 { text-align: center; }
            .article { margin-bottom: 30px; border-bottom: 1px solid #ccc; padding-bottom: 20px; }
            .title { font-size: 18px; font-weight: bold; }
            .meta { font-size: 14px; color: #555; margin-top: 5px; }
            .summary { margin-top: 10px; }
        </style>
    </head>
    <body>
        <h1>NeuroSummarizer: Weekly Digest</h1>
        {% for a in articles %}
        <div class="article">
            <div class="title">{{ a.title }}</div>
            <div class="meta">👤 {{ a.authors }}<br>📅 {{ a.publication_date }} | 🔗 <a href="{{ a.url }}">{{ a.url }}</a></div>
            <div class="summary">{{ a.summary }}</div>
        </div>
        {% endfor %}
    </body>
    </html>
    """

    template = Template(html_template)
    rendered = template.render(articles=articles)
    output_path = "/tmp/weekly_digest.pdf"
    config = pdfkit.configuration(wkhtmltopdf="/usr/bin/wkhtmltopdf")
    pdfkit.from_string(rendered, output_path, configuration=config)
    return FileResponse(output_path, media_type="application/pdf", filename="weekly_digest.pdf")


# ---------------------------------------------------------------------------
# ADMIN  — Auth
# ---------------------------------------------------------------------------

@app.post("/api/admin/login")
async def admin_login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(AdminUser).filter_by(username=payload.username).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_token(user.username)
    return {"token": token, "username": user.username}


# ---------------------------------------------------------------------------
# ADMIN  — Categories CRUD
# ---------------------------------------------------------------------------

@app.get("/api/admin/categories")
async def admin_list_categories(
    db: Session = Depends(get_db),
    _admin: str = Depends(get_current_admin),
):
    cats = db.query(Category).order_by(Category.id).all()
    result = []
    for c in cats:
        count = db.query(Article).filter(Article.category_id == c.id).count()
        result.append(_category_dict(c, count))
    return result


@app.post("/api/admin/categories")
async def admin_create_category(
    data: CategoryCreate,
    db: Session = Depends(get_db),
    _admin: str = Depends(get_current_admin),
):
    if db.query(Category).filter_by(name=data.name).first():
        raise HTTPException(status_code=409, detail="Category already exists")
    cat = Category(**data.model_dump())
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return _category_dict(cat, 0)


@app.put("/api/admin/categories/{cat_id}")
async def admin_update_category(
    cat_id: int,
    data: CategoryUpdate,
    db: Session = Depends(get_db),
    _admin: str = Depends(get_current_admin),
):
    cat = db.query(Category).filter_by(id=cat_id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(cat, field, value)
    db.commit()
    db.refresh(cat)
    count = db.query(Article).filter(Article.category_id == cat.id).count()
    return _category_dict(cat, count)


@app.delete("/api/admin/categories/{cat_id}")
async def admin_delete_category(
    cat_id: int,
    db: Session = Depends(get_db),
    _admin: str = Depends(get_current_admin),
):
    cat = db.query(Category).filter_by(id=cat_id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")
    # Remove FK references first
    db.query(Article).filter(Article.category_id == cat_id).update({Article.category_id: None})
    db.delete(cat)
    db.commit()
    return {"ok": True}


# ---------------------------------------------------------------------------
# ADMIN  — Articles management
# ---------------------------------------------------------------------------

@app.delete("/api/admin/articles/{article_id}")
async def admin_delete_article(
    article_id: int,
    db: Session = Depends(get_db),
    _admin: str = Depends(get_current_admin),
):
    art = db.query(Article).filter_by(id=article_id).first()
    if not art:
        raise HTTPException(status_code=404, detail="Article not found")
    db.delete(art)
    db.commit()
    return {"ok": True}


@app.put("/api/admin/articles/{article_id}/category")
async def admin_set_article_category(
    article_id: int,
    category_id: int = Body(..., embed=True),
    db: Session = Depends(get_db),
    _admin: str = Depends(get_current_admin),
):
    art = db.query(Article).filter_by(id=article_id).first()
    if not art:
        raise HTTPException(status_code=404, detail="Article not found")
    art.category_id = category_id
    db.commit()
    return {"ok": True}


# ---------------------------------------------------------------------------
# ADMIN  — Statistics
# ---------------------------------------------------------------------------

@app.get("/api/admin/stats")
async def admin_stats(
    db: Session = Depends(get_db),
    _admin: str = Depends(get_current_admin),
):
    total = db.query(Article).count()
    today_count = db.query(Article).filter(Article.date_added == date.today()).count()
    cat_count = db.query(Category).count()

    by_source = (
        db.query(Article.source, func.count(Article.id))
        .group_by(Article.source)
        .all()
    )

    by_category = (
        db.query(Category.display_name, Category.color, func.count(Article.id))
        .outerjoin(Article, Article.category_id == Category.id)
        .group_by(Category.id)
        .all()
    )

    # Articles per day (last 14 days)
    fourteen_ago = date.today() - timedelta(days=14)
    daily = (
        db.query(Article.date_added, func.count(Article.id))
        .filter(Article.date_added >= fourteen_ago)
        .group_by(Article.date_added)
        .order_by(Article.date_added)
        .all()
    )

    return {
        "total_articles": total,
        "added_today": today_count,
        "total_categories": cat_count,
        "by_source": {s: c for s, c in by_source},
        "by_category": [
            {"name": name, "color": color, "count": cnt}
            for name, color, cnt in by_category
        ],
        "daily": [
            {"date": d.isoformat() if d else None, "count": c}
            for d, c in daily
        ],
    }

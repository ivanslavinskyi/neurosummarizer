
from fastapi import FastAPI, Depends, Query
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse
from sqlalchemy.orm import Session
from database import SessionLocal, Article
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import csv
import io
from datetime import datetime, timedelta, date
from jinja2 import Template
import pdfkit

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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

@app.get("/api/articles/")
async def get_articles(
    db: Session = Depends(get_db),
    keyword: str = Query(None),
    source: str = Query(None),
    limit: int = Query(10),
    offset: int = Query(0),
    sort_by: str = Query("date", regex="^(date|id)$"),
    order: str = Query("desc", regex="^(asc|desc)$")
):
    query = db.query(Article)
    if keyword:
        query = query.filter(Article.keywords.ilike(f"%{keyword}%"))
    if source:
        query = query.filter(Article.source == source)

    sort_column = Article.publication_date if sort_by == "date" else Article.id
    query = query.order_by(sort_column.asc() if order == "asc" else sort_column.desc())

    total = query.count()
    articles = query.offset(offset).limit(limit).all()

    return {
        "total": total,
        "count": len(articles),
        "offset": offset,
        "limit": limit,
        "results": [article.__dict__ for article in articles]
    }

@app.get("/api/articles/count-today")
async def count_today(db: Session = Depends(get_db)):
    today = date.today()
    count = db.query(Article).filter(Article.date_added == today).count()
    return {"date": today.isoformat(), "count": count}

@app.get("/api/export/csv")
async def export_csv(db: Session = Depends(get_db)):
    articles = db.query(Article).order_by(Article.publication_date.desc()).all()

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["ID", "Title", "Authors", "Source", "Date", "Summary", "URL"])
    for a in articles:
        writer.writerow([a.id, a.title, a.authors, a.source, a.publication_date, a.summary, a.url])

    buffer.seek(0)
    return StreamingResponse(buffer, media_type="text/csv", headers={
        "Content-Disposition": "attachment; filename=articles.csv"
    })

@app.get("/api/export/json")
async def export_json(db: Session = Depends(get_db)):
    articles = db.query(Article).order_by(Article.publication_date.desc()).all()
    data = []
    for a in articles:
        item = {
            "id": a.id,
            "title": a.title,
            "authors": a.authors,
            "abstract": a.abstract,
            "summary": a.summary,
            "source": a.source,
            "publication_date": a.publication_date.isoformat(),
            "url": a.url,
            "keywords": a.keywords,
            "date_added": a.date_added.isoformat()
        }
        data.append(item)
    return JSONResponse(content=data)

@app.get("/api/export/weekly-pdf")
async def export_weekly_pdf():
    db = SessionLocal()
    today = datetime.today().date()
    week_ago = today - timedelta(days=7)
    articles = db.query(Article).filter(Article.date_added >= week_ago).order_by(Article.publication_date.desc()).all()
    db.close()

    html_template = '''
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
    '''

    template = Template(html_template)
    rendered_html = template.render(articles=articles)
    output_path = "/tmp/weekly_digest.pdf"
    config = pdfkit.configuration(wkhtmltopdf='/usr/bin/wkhtmltopdf')
    pdfkit.from_string(rendered_html, output_path, configuration=config)
    return FileResponse(output_path, media_type="application/pdf", filename="weekly_digest.pdf")

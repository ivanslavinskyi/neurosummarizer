"""
Fetch articles from arXiv for all active categories.

Reads categories and their search_queries from the database,
runs a query for each term, and saves new articles with the
correct category_id assigned.
"""
import feedparser
from urllib.parse import quote
from database import SessionLocal, Article, Category
from datetime import datetime
import time


def fetch_arxiv_articles(keyword, max_results=40, retries=3, delay=5):
    """Fetch articles from arXiv API for a single keyword."""
    encoded_keyword = quote(keyword)
    api_url = (
        f"http://export.arxiv.org/api/query?"
        f"search_query=all:{encoded_keyword}&start=0&max_results={max_results}"
        f"&sortBy=submittedDate&sortOrder=descending"
    )

    attempt = 0
    while attempt < retries:
        try:
            feed = feedparser.parse(api_url)
            articles = []

            for entry in feed.entries:
                try:
                    title = entry.title
                    authors = ", ".join(a.name for a in entry.authors)
                    abstract = entry.summary
                    pub_date = datetime.strptime(entry.published[:10], "%Y-%m-%d").date()
                    link = entry.link

                    articles.append({
                        "title": title,
                        "authors": authors,
                        "abstract": abstract,
                        "publication_date": pub_date,
                        "url": link,
                        "keywords": keyword,
                        "source": "arXiv",
                    })
                except Exception as e:
                    print(f"  Error parsing entry: {e}")
                    continue

            return articles

        except Exception as e:
            attempt += 1
            print(f"  Attempt {attempt}/{retries} failed: {e}")
            if attempt < retries:
                print(f"  Retrying in {delay}s...")
                time.sleep(delay)
            else:
                print("  All attempts failed.")
                return []


def save_articles(articles, category_id):
    """Save articles to DB, skipping duplicates. Assigns category_id."""
    db = SessionLocal()
    new_count = 0
    for art in articles:
        exists = db.query(Article).filter_by(url=art["url"]).first()
        if not exists:
            art["category_id"] = category_id
            db.add(Article(**art))
            new_count += 1
    db.commit()
    db.close()
    return new_count


def run():
    """Main entry point: iterate over active categories → fetch from arXiv."""
    db = SessionLocal()
    categories = db.query(Category).filter_by(is_active=True).all()
    db.close()

    if not categories:
        print("[arXiv] No active categories found.")
        return

    total_new = 0
    for cat in categories:
        queries = [q.strip() for q in cat.search_queries.split(",") if q.strip()]
        if not queries:
            print(f"[arXiv] Category '{cat.display_name}' has no search queries, skipping.")
            continue

        print(f"\n[arXiv] === Category: {cat.display_name} ===")
        for query in queries:
            print(f"[arXiv]   Searching: {query}")
            articles = fetch_arxiv_articles(query, max_results=20)
            saved = save_articles(articles, cat.id)
            total_new += saved
            print(f"[arXiv]   Found {len(articles)}, saved {saved} new.")
            time.sleep(3)  # Be polite to arXiv API

    print(f"\n[arXiv] Done. Total new articles: {total_new}")


if __name__ == "__main__":
    run()

import feedparser
from database import SessionLocal, Article
from datetime import datetime
import time

def fetch_arxiv_articles(keyword="glioma", max_results=30, retries=3, delay=5):
    url = (
        f"http://export.arxiv.org/api/query?"
        f"search_query=all:{keyword}&start=0&max_results={max_results}"
        f"&sortBy=submittedDate&sortOrder=descending"
    )

    attempt = 0
    while attempt < retries:
        try:
            feed = feedparser.parse(url)
            articles = []

            for entry in feed.entries:
                try:
                    title = entry.title
                    authors = ", ".join(author.name for author in entry.authors)
                    abstract = entry.summary
                    pub_date = datetime.strptime(entry.published[:10], "%Y-%m-%d").date()
                    url = entry.link

                    article = {
                        "title": title,
                        "authors": authors,
                        "abstract": abstract,
                        "publication_date": pub_date,
                        "url": url,
                        "keywords": keyword,
                        "source": "arXiv"
                    }

                    articles.append(article)

                except Exception as e:
                    print(f"Error parsing entry: {e}")
                    continue

            return articles

        except Exception as e:
            attempt += 1
            print(f"Attempt {attempt}/{retries} failed: {e}")
            if attempt < retries:
                print(f"Retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                print("All attempts failed.")
                return []

def save_articles(articles):
    db = SessionLocal()
    new_count = 0
    for art in articles:
        exists = db.query(Article).filter_by(url=art["url"]).first()
        if not exists:
            db_article = Article(**art)
            db.add(db_article)
            new_count += 1
    db.commit()
    db.close()
    print(f"Saved {new_count} new articles.")

if __name__ == "__main__":
    keyword = "glioma"
    articles = fetch_arxiv_articles(keyword=keyword, max_results=30)
    save_articles(articles)

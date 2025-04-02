from Bio import Entrez
from database import SessionLocal, Article
from datetime import datetime
import calendar

# Укажите ваш email для доступа к NCBI
Entrez.email = "mr.ivanslavinsky@gmail.com"  # ← замените на свой email

def fetch_pubmed_articles(keyword="glioma", max_results=15):
    handle = Entrez.esearch(
        db="pubmed",
        term=keyword,
        retmax=max_results,
        sort="pub+date"  # Сортировка по дате публикации
    )
    record = Entrez.read(handle)
    handle.close()

    id_list = record["IdList"]
    articles = []

    for pubmed_id in id_list:
        handle = Entrez.efetch(db="pubmed", id=pubmed_id, rettype="xml")
        records = Entrez.read(handle)
        handle.close()

        try:
            article_data = records["PubmedArticle"][0]["MedlineCitation"]["Article"]

            title = article_data.get("ArticleTitle", "No title")
            abstract = " ".join(article_data.get("Abstract", {}).get("AbstractText", ["No abstract"]))
            authors_list = article_data.get("AuthorList", [])
            authors = ", ".join(
                [f"{a.get('LastName', '')} {a.get('ForeName', '')}".strip() for a in authors_list if 'LastName' in a]
            )

            # --- корректный парсинг даты ---
            pub_info = article_data.get("Journal", {}).get("JournalIssue", {}).get("PubDate", {})
            year = pub_info.get("Year", "1900")
            month_str = pub_info.get("Month", "Jan")
            day_str = pub_info.get("Day", "01")

            try:
                month = list(calendar.month_abbr).index(month_str[:3]) if month_str[:3] in calendar.month_abbr else 1
            except ValueError:
                month = 1

            try:
                day = int(day_str)
            except:
                day = 1

            pub_date = datetime(int(year), int(month), day).date()

            url = f"https://pubmed.ncbi.nlm.nih.gov/{pubmed_id}/"

            article = {
                "title": title,
                "authors": authors,
                "abstract": abstract,
                "publication_date": pub_date,
                "url": url,
                "keywords": keyword,
                "source": "PubMed"
            }

            articles.append(article)

        except Exception as e:
            print(f"Error parsing article {pubmed_id}: {e}")
            continue

    return articles

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
    articles = fetch_pubmed_articles(keyword=keyword, max_results=15)
    save_articles(articles)

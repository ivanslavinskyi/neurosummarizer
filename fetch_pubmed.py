"""
Fetch articles from PubMed for all active categories.

Reads categories and their search_queries from the database,
runs a query for each term, and saves new articles with the
correct category_id assigned.
"""
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, date
from database import Article, Category, SessionLocal
import time


# ---------------------------------------------------------------------------
# Date extraction (unchanged logic, kept as-is)
# ---------------------------------------------------------------------------

def extract_pub_date(article):
    def try_parse_date(year, month, day):
        try:
            return datetime.strptime(
                f"{year}-{int(month):02d}-{int(day):02d}", "%Y-%m-%d"
            ).date()
        except Exception:
            return None

    article_date = article.find(".//ArticleDate")
    if article_date is not None:
        y = article_date.findtext("Year")
        m = article_date.findtext("Month")
        d = article_date.findtext("Day")
        d1 = try_parse_date(y, m, d)
        if d1:
            return d1

    pub_date = article.find(".//PubDate")
    if pub_date is not None:
        y = pub_date.findtext("Year")
        m = pub_date.findtext("Month", "01")
        d = pub_date.findtext("Day", "01")
        try:
            m = datetime.strptime(m[:3], "%b").month if not m.isdigit() else int(m)
        except Exception:
            m = 1
        d2 = try_parse_date(y, m, d)
        if d2:
            return d2

    pm_date = article.find(".//PubMedPubDate")
    if pm_date is not None:
        y = pm_date.findtext("Year")
        m = pm_date.findtext("Month")
        d = pm_date.findtext("Day")
        d3 = try_parse_date(y, m, d)
        if d3:
            return d3

    return date.today()


# ---------------------------------------------------------------------------
# PubMed fetcher — now per-query
# ---------------------------------------------------------------------------

def fetch_pubmed_for_query(query, category_id, max_results=42):
    """Search PubMed for a single query and save results with category_id."""
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
    search_url = (
        f"{base_url}esearch.fcgi?db=pubmed"
        f"&term={requests.utils.quote(query)}"
        f"&retmode=json&retmax={max_results}"
    )

    try:
        response = requests.get(search_url, timeout=30)
        response.raise_for_status()
        id_list = response.json()["esearchresult"]["idlist"]
    except Exception as e:
        print(f"  Search failed: {e}")
        return 0

    if not id_list:
        return 0

    try:
        fetch_url = f"{base_url}efetch.fcgi?db=pubmed&id={','.join(id_list)}&retmode=xml"
        fetch_response = requests.get(fetch_url, timeout=60)
        fetch_response.raise_for_status()
        root = ET.fromstring(fetch_response.content)
    except Exception as e:
        print(f"  Fetch failed: {e}")
        return 0

    new_articles = 0
    session = SessionLocal()

    with open("pubmed_log.txt", "a") as log:
        for article in root.findall(".//PubmedArticle"):
            try:
                title_elem = article.find(".//ArticleTitle")
                title = "".join(title_elem.itertext()).strip() if title_elem is not None else ""

                abstract_elem = article.find(".//AbstractText")
                abstract = "".join(abstract_elem.itertext()).strip() if abstract_elem is not None else ""

                if not abstract:
                    log.write(f"[{datetime.now()}] Skipped (empty abstract): {title}\n")
                    continue

                authors_list = article.findall(".//Author")
                authors = ", ".join([
                    a.findtext("LastName", "") + " " + a.findtext("ForeName", "")
                    for a in authors_list if a.find("LastName") is not None
                ])

                pub_date = extract_pub_date(article)
                url = f"https://pubmed.ncbi.nlm.nih.gov/{article.findtext('.//PMID')}/"

                # Duplicate check
                exists = session.query(Article).filter_by(title=title, source="PubMed").first()
                if exists:
                    continue

                db_article = Article(
                    title=title,
                    authors=authors,
                    abstract=abstract,
                    summary=None,
                    source="PubMed",
                    publication_date=pub_date,
                    url=url,
                    keywords=query,
                    category_id=category_id,
                )
                session.add(db_article)
                session.commit()
                new_articles += 1

                log.write(f"[{datetime.now()}] Saved: {title} | {pub_date} | cat_id={category_id}\n")

            except Exception as e:
                log.write(f"[{datetime.now()}] Error parsing article: {str(e)}\n")

    session.close()
    return new_articles


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run():
    """Iterate over active categories → fetch from PubMed for each query."""
    db = SessionLocal()
    categories = db.query(Category).filter_by(is_active=True).all()
    db.close()

    if not categories:
        print("[PubMed] No active categories found.")
        return

    total_new = 0
    for cat in categories:
        queries = [q.strip() for q in cat.search_queries.split(",") if q.strip()]
        if not queries:
            print(f"[PubMed] Category '{cat.display_name}' has no search queries, skipping.")
            continue

        print(f"\n[PubMed] === Category: {cat.display_name} ===")
        for query in queries:
            print(f"[PubMed]   Searching: {query}")
            saved = fetch_pubmed_for_query(query, cat.id, max_results=20)
            total_new += saved
            print(f"[PubMed]   Saved {saved} new articles.")
            time.sleep(1)  # NCBI rate limit: 3 req/sec without API key

    print(f"\n[PubMed] Done. Total new articles: {total_new}")


if __name__ == "__main__":
    run()
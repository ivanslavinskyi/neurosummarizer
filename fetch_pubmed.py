import os
import requests
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from datetime import datetime, date
from database import Article, SessionLocal

# Helper function to extract publication date from article
def extract_pub_date(article):
    def try_parse_date(year, month, day):
        try:
            return datetime.strptime(f"{year}-{int(month):02d}-{int(day):02d}", "%Y-%m-%d").date()
        except Exception:
            return None

    article_date = article.find(".//ArticleDate")
    if article_date is not None:
        y = article_date.findtext("Year")
        m = article_date.findtext("Month")
        d = article_date.findtext("Day")
        date1 = try_parse_date(y, m, d)
        if date1:
            return date1

    pub_date = article.find(".//PubDate")
    if pub_date is not None:
        y = pub_date.findtext("Year")
        m = pub_date.findtext("Month", "01")
        d = pub_date.findtext("Day", "01")
        try:
            m = datetime.strptime(m[:3], "%b").month if not m.isdigit() else int(m)
        except:
            m = 1
        date2 = try_parse_date(y, m, d)
        if date2:
            return date2

    pm_date = article.find(".//PubMedPubDate")
    if pm_date is not None:
        y = pm_date.findtext("Year")
        m = pm_date.findtext("Month")
        d = pm_date.findtext("Day")
        date3 = try_parse_date(y, m, d)
        if date3:
            return date3

    return date.today()

def fetch_pubmed_articles():
    query = "glioma"
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
    search_url = f"{base_url}esearch.fcgi?db=pubmed&term={query}&retmode=json&retmax=32"
    response = requests.get(search_url)
    id_list = response.json()['esearchresult']['idlist']

    fetch_url = f"{base_url}efetch.fcgi?db=pubmed&id={','.join(id_list)}&retmode=xml"
    fetch_response = requests.get(fetch_url)
    root = ET.fromstring(fetch_response.content)

    new_articles = 0
    session = SessionLocal()

    with open("pubmed_log.txt", "a") as log:
        for article in root.findall(".//PubmedArticle"):
            try:
                title = article.findtext(".//ArticleTitle", default="").strip()
                abstract = article.findtext(".//AbstractText", default="").strip()

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
                    keywords="glioma"
                )
                session.add(db_article)
                session.commit()
                new_articles += 1

                log.write(f"[{datetime.now()}] Saved: {title} | {pub_date}\n")

            except Exception as e:
                log.write(f"[{datetime.now()}] Error parsing article: {str(e)}\n")

    print(f"Saved {new_articles} new articles.")

if __name__ == "__main__":
    fetch_pubmed_articles()

"""
Summarise articles that have no summary yet.

Uses OpenAI GPT-4o-mini (cheaper and better than gpt-3.5-turbo).
Includes retry logic and error handling.
"""
import openai
import os
import time
from dotenv import load_dotenv
from database import SessionLocal, Article

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

MODEL = "gpt-4o-mini"
MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds


def summarize_article(article_id, abstract):
    """Generate a summary for a single article."""
    abstract = (abstract or "")[:8000]
    if not abstract.strip():
        print(f"  Skipping article {article_id}: empty abstract.")
        return

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = openai.chat.completions.create(
                model=MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a research assistant. Read the abstract of this "
                            "neuroscience article and write a 1–2 sentence summary in "
                            "plain English, even if the abstract is incomplete."
                        ),
                    },
                    {"role": "user", "content": abstract},
                ],
                temperature=0.5,
                max_tokens=300,
            )

            summary = response.choices[0].message.content.strip()

            db = SessionLocal()
            article = db.get(Article, article_id)
            if article:
                article.summary = summary
                db.commit()
                print(f"  ✓ Summarised: {article.title[:80]}...")
            else:
                print(f"  Article ID {article_id} not found in DB.")
            db.close()
            return  # success

        except Exception as e:
            print(f"  Attempt {attempt}/{MAX_RETRIES} failed for article {article_id}: {e}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY)
            else:
                print(f"  ✗ All retries exhausted for article {article_id}.")


def summarize_articles_without_summary():
    """Find and summarise all articles that lack a summary."""
    db = SessionLocal()
    articles = db.query(Article).filter(Article.summary.is_(None)).all()
    ids_and_abstracts = [(a.id, a.abstract, a.title) for a in articles]
    db.close()

    total = len(ids_and_abstracts)
    if total == 0:
        print("[summarize] All articles already have summaries.")
        return

    print(f"[summarize] {total} articles need summarisation (model: {MODEL})")
    for i, (aid, abstract, title) in enumerate(ids_and_abstracts, 1):
        print(f"[{i}/{total}] {title[:70]}...")
        summarize_article(aid, abstract)
        time.sleep(0.5)  # gentle rate limiting

    print(f"\n[summarize] Done.")


if __name__ == "__main__":
    summarize_articles_without_summary()

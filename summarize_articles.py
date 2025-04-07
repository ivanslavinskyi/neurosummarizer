import openai
import os
from dotenv import load_dotenv
from database import SessionLocal, Article

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

def summarize_article(article_id, abstract):
    try:
        abstract = abstract[:8000]  # Ensure abstract length is within token limits

        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a research assistant. Read the abstract of this neuroscience article and write a 1–2 sentence summary in plain English, even if the abstract is incomplete."},
                {"role": "user", "content": abstract},
            ],
            temperature=0.5,
            max_tokens=1000
        )

        summary = response.choices[0].message.content.strip()

        db = SessionLocal()
        article = db.get(Article, article_id)  # Recommended modern method
        if article:
            article.summary = summary
            db.commit()
            print(f"Successfully summarized: {article.title}")
        else:
            print(f"Article with ID {article_id} not found.")
        db.close()

    except Exception as e:
        print(f"Error summarizing article {article_id}: {e}")

def summarize_articles_without_summary():
    db = SessionLocal()
    articles = db.query(Article).filter(Article.summary == None).all()
    db.close()  # Close session after fetching IDs and abstracts

    for article in articles:
        print(f"Summarizing article: {article.title}")
        summarize_article(article.id, article.abstract)

if __name__ == "__main__":
    summarize_articles_without_summary()



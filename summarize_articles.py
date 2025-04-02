from openai import OpenAI
from database import SessionLocal, Article
from dotenv import load_dotenv
import os

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def summarize_text(text):
    prompt = f"Summarize briefly the following neuroscience article abstract:\n\n{text}\n\nSummary:"
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=150,
        temperature=0.5,
    )
    summary = response.choices[0].message.content.strip()
    return summary

def summarize_unsummarized_articles():
    db = SessionLocal()
    articles = db.query(Article).filter(Article.summary.is_(None)).all()
    for article in articles:
        print(f"Summarizing article: {article.title}")
        article.summary = summarize_text(article.abstract)
        db.commit()
    db.close()

if __name__ == "__main__":
    summarize_unsummarized_articles()


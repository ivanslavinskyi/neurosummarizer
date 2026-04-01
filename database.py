"""
Database models and migration utilities for NeuroSummarizer.

Models:
  - Category: topic categories for articles (glioma, epilepsy, etc.)
  - Article:  scientific articles with FK to category
  - AdminUser: admin panel credentials
"""
from sqlalchemy import (
    create_engine, Column, Integer, String, Date, Text,
    Boolean, DateTime, ForeignKey, inspect, text
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime, date

engine = create_engine(
    "sqlite:///database/articles.db",
    connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)          # slug: "glioma"
    display_name = Column(String)                            # "Glioma Research"
    search_queries = Column(Text, default="")                # comma-separated terms
    color = Column(String, default="#3b82f6")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    articles = relationship("Article", back_populates="category")


class Article(Base):
    __tablename__ = "articles"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    authors = Column(String)
    abstract = Column(Text)
    summary = Column(Text)
    source = Column(String)                                  # "arXiv" / "PubMed"
    publication_date = Column(Date)
    url = Column(String)
    keywords = Column(String)
    date_added = Column(Date, default=date.today)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)

    category = relationship("Category", back_populates="articles")


class AdminUser(Base):
    __tablename__ = "admin_users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)


# ---------------------------------------------------------------------------
# Migration helper
# ---------------------------------------------------------------------------

def migrate_db():
    """
    Safely upgrade an existing database:
      1. Create new tables (categories, admin_users) if missing.
      2. Add `category_id` column to articles if missing.
    Idempotent — safe to call on every app startup.
    """
    # Create tables that don't exist yet
    Base.metadata.create_all(bind=engine)

    inspector = inspect(engine)
    if inspector.has_table("articles"):
        columns = [col["name"] for col in inspector.get_columns("articles")]
        if "category_id" not in columns:
            with engine.connect() as conn:
                conn.execute(text(
                    "ALTER TABLE articles ADD COLUMN category_id INTEGER REFERENCES categories(id)"
                ))
                conn.commit()
            print("[migrate] Added category_id column to articles table.")
        else:
            print("[migrate] articles table already up to date.")
    else:
        print("[migrate] articles table will be created by create_all.")


# Create tables on first import (handles fresh installs)
Base.metadata.create_all(bind=engine)

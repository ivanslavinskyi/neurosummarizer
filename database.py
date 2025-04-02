from sqlalchemy import create_engine, Column, Integer, String, Date, Text
from sqlalchemy.orm import declarative_base, sessionmaker
import datetime

engine = create_engine("sqlite:///database/articles.db")
SessionLocal = sessionmaker(bind=engine)

Base = declarative_base()

class Article(Base):
    __tablename__ = 'articles'

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    authors = Column(String)
    abstract = Column(Text)
    summary = Column(Text)
    source = Column(String)  # arXiv или PubMed
    publication_date = Column(Date)
    url = Column(String)
    keywords = Column(String)
    date_added = Column(Date, default=datetime.date.today)

Base.metadata.create_all(bind=engine)

"""
One-time initialisation / migration script.

Run once after updating the code to:
  1. Migrate the database schema  (add category_id to articles)
  2. Seed default categories
  3. Seed the admin user
  4. Assign existing articles to the "Glioma" category

Usage:
    python init_db.py
"""
import os
from dotenv import load_dotenv
from database import SessionLocal, migrate_db, Category, Article, AdminUser
from auth import hash_password

load_dotenv()


# --------------- config ---------------
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "neuro2026!")

INITIAL_CATEGORIES = [
    {
        "name": "glioma",
        "display_name": "Glioma Research",
        "search_queries": "glioma,glioblastoma,GBM,brain tumor,astrocytoma",
        "color": "#ef4444",
        "is_active": True,
    },
    {
        "name": "neurodegenerative",
        "display_name": "Neurodegenerative Diseases",
        "search_queries": "neurodegenerative,Alzheimer,Parkinson,ALS,dementia,Huntington",
        "color": "#8b5cf6",
        "is_active": True,
    },
    {
        "name": "neuroimaging",
        "display_name": "Brain Imaging / Neuroimaging",
        "search_queries": "neuroimaging,brain imaging,fMRI,MRI brain,PET brain,diffusion tensor",
        "color": "#3b82f6",
        "is_active": True,
    },
    {
        "name": "epilepsy",
        "display_name": "Epilepsy",
        "search_queries": "epilepsy,seizure,anticonvulsant,epileptic,antiepileptic",
        "color": "#10b981",
        "is_active": True,
    },
]


def seed_categories(db):
    created = 0
    for cat_data in INITIAL_CATEGORIES:
        exists = db.query(Category).filter_by(name=cat_data["name"]).first()
        if not exists:
            db.add(Category(**cat_data))
            created += 1
    db.commit()
    print(f"[seed] Created {created} categories ({len(INITIAL_CATEGORIES) - created} already existed).")


def seed_admin(db):
    exists = db.query(AdminUser).filter_by(username=ADMIN_USERNAME).first()
    if exists:
        print(f"[seed] Admin user '{ADMIN_USERNAME}' already exists.")
        return
    admin = AdminUser(
        username=ADMIN_USERNAME,
        password_hash=hash_password(ADMIN_PASSWORD),
    )
    db.add(admin)
    db.commit()
    print(f"[seed] Created admin user: {ADMIN_USERNAME}")
    if ADMIN_PASSWORD == "neuro2026!":
        print("[seed] ⚠️  Using DEFAULT password. Set ADMIN_PASSWORD in .env for production!")


def assign_existing_articles(db):
    """Assign articles that have no category to the first matching category."""
    glioma = db.query(Category).filter_by(name="glioma").first()
    if not glioma:
        print("[seed] Glioma category not found, skipping article assignment.")
        return
    updated = (
        db.query(Article)
        .filter(Article.category_id.is_(None))
        .update({Article.category_id: glioma.id})
    )
    db.commit()
    print(f"[seed] Assigned {updated} existing articles to category 'Glioma'.")


if __name__ == "__main__":
    print("=" * 50)
    print("  NeuroSummarizer — DB Migration & Seed")
    print("=" * 50)

    # 1. Migrate schema
    migrate_db()

    # 2. Seed data
    db = SessionLocal()
    try:
        seed_categories(db)
        seed_admin(db)
        assign_existing_articles(db)
    finally:
        db.close()

    print("\n✅  Done! You can now start the app with:")
    print("    uvicorn main:app --reload")

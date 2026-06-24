"""
Slug generation utilities.
"""
import re
from sqlalchemy.orm import Session

from models import Proposal


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(
        r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF'
        r'\U0001F1E0-\U0001F1FF\U00002700-\U000027BF\U0001F900-\U0001F9FF'
        r'\U0001FA00-\U0001FA6F\U0001FA70-\U0001FAFF\U00002600-\U000026FF'
        r'\U0000FE00-\U0000FE0F\U0000200D]+', '', text)
    text = re.sub(r'[\s._/]+', '-', text)
    text = re.sub(r'[^\w-]', '', text)
    text = re.sub(r'-+', '-', text)
    return text.strip('-')


def generate_unique_slug(db: Session, base_text: str) -> str:
    slug = slugify(base_text)
    if not slug:
        slug = "proposal"
    existing = db.query(Proposal).filter(Proposal.slug == slug).first()
    if not existing:
        return slug
    counter = 1
    while True:
        candidate = f"{slug}-{counter}"
        if not db.query(Proposal).filter(Proposal.slug == candidate).first():
            return candidate
        counter += 1

import uuid
from sqlalchemy import Column, Integer, String, Text, Float, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from .base import Base


class Category(Base):
    __tablename__ = "categories"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    products = relationship("Product", back_populates="category_rel")


class Product(Base):
    __tablename__ = "products"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    base_price = Column(Float, nullable=False)
    features = Column(Text, nullable=False, default="[]")
    category = Column(String(255), nullable=True)
    category_id = Column(String(36), ForeignKey("categories.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    is_retainer = Column(Boolean, default=False)
    monthly_ads_cost = Column(Float, nullable=True, default=5000000)
    roi_months = Column(Integer, nullable=True, default=3)
    roi_multiplier = Column(Float, nullable=True, default=3.5)
    comparison_points = Column(Text, nullable=True)
    category_rel = relationship("Category", back_populates="products")


class DynamicTemplate(Base):
    __tablename__ = "dynamic_templates"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    type = Column(String(255), nullable=False)  # WA_BLAST, PROPOSAL_TEXT, PROPOSAL_INTRO, PROPOSAL_OUTRO, FOLLOW_UP, GENERAL, TIMELINE_TEMPLATE
    content = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True)
    category_id = Column(String(36), ForeignKey("categories.id"), nullable=True)
    category_rel = relationship("Category")

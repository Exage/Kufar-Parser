from sqlalchemy import Column, Integer, String, Text, Numeric, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func

Base = declarative_base()


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True)
    kufar_id = Column(String(100), unique=True, nullable=False, index=True)

    title = Column(String(500), nullable=False)
    price = Column(Numeric(10, 2), nullable=True)
    url = Column(Text, nullable=False)

    rule_name = Column(String(255), nullable=False)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    notifications = relationship("Notification", back_populates="product")


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True)

    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    rule_name = Column(String(255), nullable=False)

    sent_at = Column(DateTime, server_default=func.now())

    product = relationship("Product", back_populates="notifications")
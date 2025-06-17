from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, Boolean, func
from sqlalchemy.orm import relationship

from app.backend.db import Base


class Review(Base):
    __tablename__ = 'reviews'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    product_id = Column(Integer, ForeignKey('products.id'))
    comment = Column(String(512), nullable=True)
    comment_data = Column(DateTime, default=func.now())
    grade = Column(Integer)
    is_active = Column(Boolean, default=True)

    product = relationship('Product', back_populates='reviews', uselist=False)
    user = relationship('User', back_populates='reviews', uselist=True)

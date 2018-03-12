from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, validates
from sqlalchemy import create_engine

Base = declarative_base()

class Category(Base):
    __tablename__ = 'category'
   
    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)

class ListItem(Base):
    __tablename__ = 'list_item'

    id = Column(Integer, primary_key=True)
    name =Column(String(80), nullable=False)
    description = Column(String(360))
    category_id = Column(Integer, ForeignKey('category.id'))
    category = relationship(Category)
   
engine = create_engine('sqlite:///itemcatalog.db')
Base.metadata.create_all(engine)

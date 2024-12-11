from sqlalchemy import create_engine, Column, String, Integer, ForeignKey, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from settings import settings


Base = declarative_base()

engine = create_engine(settings.postgres.url, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Directory(Base):
    __tablename__ = "directories"
    id = Column(Integer, primary_key=True, index=True)
    path = Column(String, unique=True, index=True)
    is_indexed = Column(Boolean, default=False)

    images = relationship("Image", back_populates="directory")


class Image(Base):
    __tablename__ = "images"
    id = Column(Integer, primary_key=True, index=True)
    path = Column(String, unique=True, index=True)
    directory_id = Column(Integer, ForeignKey("directories.id"))
    is_indexed = Column(Boolean, default=False)

    directory = relationship("Directory", back_populates="images")


Base.metadata.create_all(bind=engine)

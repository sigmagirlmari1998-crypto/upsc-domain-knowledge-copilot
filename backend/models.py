from datetime import datetime
from sqlalchemy import (Column, Integer, String, DateTime, ForeignKey,
                        Text, LargeBinary)
from sqlalchemy.orm import relationship
from backend.db import Base


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String(80), unique=True, nullable=False, index=True)
    email = Column(String(200), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    corpora = relationship("Corpus", back_populates="user",
                           cascade="all, delete-orphan")


class Corpus(Base):
    __tablename__ = "corpora"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"),
                     nullable=False, index=True)
    name = Column(String(200), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="corpora")
    documents = relationship("Document", back_populates="corpus",
                             cascade="all, delete-orphan")
    messages = relationship("ChatMessage", back_populates="corpus",
                            cascade="all, delete-orphan")


class Document(Base):
    """One row per uploaded file. Stores all chunks + embeddings as a blob."""
    __tablename__ = "documents"
    id = Column(Integer, primary_key=True)
    corpus_id = Column(Integer, ForeignKey("corpora.id", ondelete="CASCADE"),
                       nullable=False, index=True)
    filename = Column(String(400), nullable=False)
    chunks_json = Column(Text, nullable=False)        # JSON list of {source,page,text}
    embeddings_npy = Column(LargeBinary, nullable=False)  # np.save bytes
    created_at = Column(DateTime, default=datetime.utcnow)

    corpus = relationship("Corpus", back_populates="documents")


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id = Column(Integer, primary_key=True)
    corpus_id = Column(Integer, ForeignKey("corpora.id", ondelete="CASCADE"),
                       nullable=False, index=True)
    role = Column(String(20), nullable=False)   # "user" | "assistant"
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

    corpus = relationship("Corpus", back_populates="messages")
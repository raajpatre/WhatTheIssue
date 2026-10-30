from sqlalchemy import Column, Integer, String, Text
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class RepoRow(Base):
    __tablename__ = "repos"

    full_name = Column(String, primary_key=True)
    etag = Column(String, nullable=True)
    last_fetched_at = Column(String, nullable=True)


class IssueRow(Base):
    __tablename__ = "issues"

    id = Column(Integer, primary_key=True)
    repo = Column(String, nullable=False)
    number = Column(Integer, nullable=False)
    payload = Column("json", Text, nullable=False)
    updated_at = Column(String, nullable=False)


class SeenIssueRow(Base):
    __tablename__ = "seen_issues"

    repo = Column(String, primary_key=True)
    issue_id = Column(Integer, primary_key=True)


class AIInsightRow(Base):
    __tablename__ = "ai_insights"

    repo = Column(String, primary_key=True)
    number = Column(Integer, primary_key=True)
    payload = Column("json", Text, nullable=False)
    created_at = Column(String, nullable=False)


class WatchRow(Base):
    __tablename__ = "watches"

    id = Column(Integer, primary_key=True, autoincrement=True)
    repo = Column(String, nullable=False)
    tags_json = Column(Text, nullable=False)
    channel = Column(String, nullable=False)
    contact = Column(String, nullable=False)
    created_at = Column(String, nullable=False)

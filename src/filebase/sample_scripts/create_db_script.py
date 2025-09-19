from src.filebase.models import Base
from filebase.connection import engine
from sqlalchemy import text



with engine.begin() as conn:
    conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))

Base.metadata.create_all(bind=engine)
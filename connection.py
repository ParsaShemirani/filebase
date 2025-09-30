from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from settings import database_path

url = "sqlite:///" + database_path

engine = create_engine(url, echo=False)

Session = sessionmaker(bind=engine)
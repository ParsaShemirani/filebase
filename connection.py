from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from env_vars import DATABASE_PATH_STR

engine = create_engine("sqlite:///" + DATABASE_PATH_STR, echo=False)

Session = sessionmaker(bind=engine)
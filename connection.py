from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from env_vars import DATABASE_PATH

engine = create_engine("sqlite:///" + str(DATABASE_PATH), echo=False)

Session = sessionmaker(bind=engine)
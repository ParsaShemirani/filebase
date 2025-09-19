from sqlalchemy import create_engine, URL
from sqlalchemy.orm import sessionmaker


url_object = URL.create(
    drivername="postgresql+psycopg", username="postgres",
    password="postgres",
    host="localhost",
    port=8432,
    database="filebase"
)

engine = create_engine(url_object, echo=True)

Session = sessionmaker(bind=engine)


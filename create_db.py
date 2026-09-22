from models import Base
from db_funcs import engine

Base.metadata.create_all(engine)
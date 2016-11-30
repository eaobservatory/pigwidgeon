from sqlalchemy.orm import sessionmaker
import os
from sqlalchemy import create_engine
from db import Base

# State for the info sublists
class isType:
    RADIO = 0
    CHECK = 1
    NOTES = 2
    TEXTPERLINE = 3

def get_db_session(engine):
    # Set up DB stuff.
    Session = sessionmaker(bind=engine)
    ses = Session()
    return ses


def create_session():
    if os.path.exists('mydatabase.db'):
        engine = create_engine('sqlite:///mydatabase.db')
    else:
        engine = create_engine('sqlite:///mydatabase.db')
        Base.metadata.create_all(engine)
    session = get_db_session(engine)
    return session

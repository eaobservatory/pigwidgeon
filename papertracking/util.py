from sqlalchemy.orm import sessionmaker
import os
from sqlalchemy import create_engine
from .db import Base
from .config import get_config



# State for the info sublists
class isType:
    RADIO = 0
    CHECK = 1
    NOTES = 2
    TEXTPERLINE = 3


def create_session():
    config = get_config()

    dbconfig = config['DATABASE']
    dburl = dbconfig['url']

    # elif dbtype == 'sqlite':
    #     dbpath = dbconfig['dbfilename']
    #     if os.path.exists('dbpath'):
    #         engine = create_engine('sqlite:///{}'.format(dbpath))
    #     else:
    #         engine = create_engine('sqlite:///{}'.format(dbpath))
    #         Base.metadata.create_all(engine)

    engine = create_engine(dburl, echo=bool(dbconfig.get('echo', 0)))
    session = sessionmaker(bind=engine)
    return session()

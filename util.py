from sqlalchemy.orm import sessionmaker
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

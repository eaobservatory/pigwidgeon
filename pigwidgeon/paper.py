from .db import Search, Paper
def get_paper_info(paperid, searchid, session):
    """
    Get summary info of paper.
    """

    paperid = int(paperid)
    searchid = int(searchid)

    ses = session

    # Get search and paper
    search = ses.query(Search).filter(Search.id==searchid).one()
    paper = ses.query(Paper).filter(Paper.id==paperid).one()

    # Check if paper is in search: display warning if not?
    # More efficient way to do this?
    if search.id in [i.id for i in paper.searches]:
        paper_belongs = True
    else:
        paper_belongs = False
    return search, paper

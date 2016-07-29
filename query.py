# -*- coding: utf-8 -*-
import ads
import logging


logger = logging.getLogger(__name__)

# Turn off logging from requests and urllib3 (again)
#logging.getLogger("requests").setLevel(logging.WARNING)
#logging.getLogger('urllib3').setLevel(logging.WARNING)


# Does not have a test???
def get_ads_results(querystring, datefrom=None, dateto=None):
    """
    Carry out ADS query, optionally limit by daterange.

    querystring (str): an ADS bumblebee query.
    datefrom (opt, str): starting publication date in YYYY-MM format.
    dateto (opt, str): end publication date in YYYY-MM format.

    Dates are inclusive.

    Returns a list of ads.search.Article objects
    """

    # Set up correct date range if requeseted.
    if datefrom and not dateto:
        dateto = '*'
    elif dateto and not datefrom:
        datefrom = '*'

    if datefrom and dateto:
        daterange = '[{0} TO {1}]'.format(datefrom, dateto)
        querystring += ' AND pubdate:' + daterange

    # Define which values we want to get.
    fl=['id', 'abstract', 'doi', 'author', 'bibcode',
        'title', 'pubdate', 'property',
        'keyword', 'identifier']


    # Carry out query.
    query = ads.search.SearchQuery(q=querystring, sort='date asc', fl=fl)
    query.execute()
    logger.debug('Found {0} articles'.format(query.progress))

    # I'm sure there's a more correct way to do this?
    while len(query.articles) < query.response.numFound:
        query.execute()
        logger.debug('Found {0} articles'.format(query.progress))

    logger.info('Retrieved records for {0} articles.'.format(
        len(query.articles)))
    return query.articles


def create_paper_objects(article):
    """
    Turn ADS article object into DB Paper object.
    """
    pub_openaccess =  'PUB_OPENACCESS' in article.property
    refereed = 'REFEREED' in article.property

    ids=[Identifier(identifier=i) for i in article.identifier]
    keywords = [Keyword(keyword=k) for k in article.keyword]

    paper = Paper(bibcode = article.bibcode,
                  title = article.title,
                  abstract = article.abstract,
                  doi = article.doi,
                  pub_openaccess = pub_openacces,
                  refereed = refereed,
                  identifiers = ids,
                  keywords = keywords)
    return paper

def add_papers_to_db(papers, databaseidentifier):
    """
    Add a list of paper objects to database.

    Check if they are new, add them if so. If they already exist,
    check if any information has changed and update with new
    information as necessary.

    """
    engine = create_engine(databaseidentifier)
    Session = sessionmaker(bind=engine)
    session = Session()

    for paper in papers:
        # First check if paper in db:
        match = check_if_paper_in_db(paper, session)

        # If no match, add paper as new paper
        if not match:
            session.add(paper)

        # If there is a match, check if it needs to be updated.
        else:
            check_and_update(paper, session)




def check_if_paper_in_db(paper, session):

    # If bibcode matches, then definitely in
    try:
        match = session.query(Paper).filter(Paper.bibcode==bibcode).one()
    except sqlalchemy.orm.exc.NoResultFound:
        # Check all identifiers
        try:
            match = ses.query(Paper).join(Identifier).filter(
                Identifier.identifier.in_(paper.identifiers)).one()
        except sqlalchemy.orm.exc.NoresultFound:
            match = None
    # Add check for multiple results? Don't know if this ever can
    # happen?
    return match


def create_new_search(name, ads_querystring,
                   startdate,
                   papertypes,
                   infosections):
    """
    Add a new search.

    name: string, short name for search
    ads_querystring: string to pass to ads to perform query
    startdate: first date to start checking from.
    papertypes: ordered list of PaperType objects
    infosections: ordered list of InfoSection objects

    """
    Search(name=name,
           ads_query

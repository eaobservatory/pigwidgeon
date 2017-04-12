# -*OA- coding: utf-8 -*-OA
import ads
import logging
import datetime
import sqlalchemy
import itertools
from .db import Search, Paper, Identifier, Keyword, Author

logger = logging.getLogger(__name__)

# Turn off logging from requests and urllib3 (again)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)


def update_search(searchid, session, dryrun=False):
    search = session.query(Search).filter(Search.id==searchid).one()
    #datefrom:
    if search.last_performed is None:
        datefrom=search.startdate
    else:
        # Roughly 3 months?
        delta = datetime.timedelta(days=31*search.timerange)
        datefrom = search.last_performed - delta
    adsresults = get_ads_results(search.ads_query, datefrom=datefrom, dateto=None)
    lastperformed = datetime.datetime.now()
    papers = [create_paper_objects(article, search) for article in adsresults]
    add_papers_to_db(papers, session, dryrun=dryrun)

    # Update search with last performed date (do this last in case of issues)
    if not dryrun:
        search.last_performed = lastperformed
        session.commit()

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
    if datefrom:
        datefrom = '\"{}\"'.format(datefrom.strftime('%Y-%m-%dT%H:%M:%S'))
    if dateto:
        dateto = '\"{}\"'.format(dateto.strftime('%Y-%m-%dT%H:%M:%S'))
    if datefrom and not dateto:
        dateto = '*'
    elif dateto and not datefrom:
        datefrom = '*'

    if datefrom and dateto:
        daterange = '[{0} TO {1}]'.format(datefrom, dateto)
        querystring = '({}) AND pubdate:{}'.format(querystring, daterange)

    # Define which values we want to get.
    fl=['id', 'abstract', 'doi', 'author', 'aff', 'bibcode',
        'title', 'pubdate', 'property',
        'keyword', 'identifier', 'alternate_bibcode', 'doctype']

    print('Querying ads with {}'.format(querystring))
    # Carry out query.
    query = ads.search.SearchQuery(q=querystring, sort='date asc', fl=fl)
    query.execute()
    print('Found {} articles'.format(query.progress))
    logger.debug('Found {0} articles'.format(query.progress))

    # I'm sure there's a more correct way to do this?
    while len(query.articles) < query.response.numFound:
        query.execute()
        print('Found {} articles'.format(query.progress))
        logger.debug('Found {0} articles'.format(query.progress))

    logger.info('Retrieved records for {0} articles.'.format(
        len(query.articles)))
    return query.articles


def create_paper_objects(article, search):
    """
    Turn ADS article object into DB Paper object.
    """
    pub_openaccess =  'PUB_OPENACCESS' in article.property
    refereed = 'REFEREED' in article.property
    if article.author:
        authorlist = list(itertools.zip_longest(article.author, article.aff))
        authors = [Author(author=i, position_=article.author.index(i), affiliation=a) for i,a in authorlist]
    else:
        authors = []
    ids=[Identifier(identifier=i) for i in article.identifier]
    if article.keyword:
        keywords = [Keyword(keyword=k) for k in article.keyword]
    else:
        keywords=[]
    if article.doi:
        if len(article.doi) > 1:
            print('Found multiple dois for {}: {}'.format(article.bibcode, article.di))
        doi=article.doi[0]
    else:
        doi=None

    try:
        pubdate = datetime.datetime.strptime(article.pubdate, '%Y-%m-00').date()
    except ValueError:
        try:
            pubdate = datetime.datetime.strptime(article.pubdate, '%Y-00-00').date()
        except ValueError:
            pubdate = None
            logger.warning('Could not find pubdate for article {}: format was {}'.format(
                article.bibcode, article.pubdate))

    paper = Paper(bibcode = article.bibcode,
                  title = article.title[0],
                  abstract = article.abstract,
                  pubdate = pubdate,
                  doi = doi,
                  pub_openaccess = pub_openaccess,
                  refereed = refereed,
                  identifiers = ids,
                  keywords = keywords,
                  authors=authors,
                  searches=[search])
    return paper

def add_papers_to_db(papers, session, dryrun=False):
    """
    Add a list of paper objects to database.

    Check if they are new, add them if so. If they already exist,
    check if any information has changed and update with new
    information as necessary.

    Update the search

    """

    updated=set()
    new=set()
    for paper in papers:
        # First check if paper in db:
        match = check_if_paper_in_db(paper, session)

        # If no match, add paper as new paper
        if not match:
            if not dryrun:
                session.add(paper)
                logger.debug('Added {}: to database'.format(paper.bibcode))
            else:
                logger.debug('DRYRUN: would have added {} to database'.format(paper.bibcode))
            new.add(paper.bibcode)

        # If there is a match, check if it needs to be updated.
        else:
            updated.update(check_and_update(match,paper, session, dryrun=dryrun))
    if not dryrun:
        session.commit()
        logger.info('Added {} new papers to database.'.format(len(new)))
        logger.info('Update {} existing papers in database.'.format(len(updated)))
        logger.debug('Updated {}'.format('\n'.join(list(updated))))
    if dryrun:
        logger.info('DRYRUN: would have added {} new papers to database.'.format(len(new)))
        logger.info('DRYRUN: would have Updated {} existing papers in database.'.format(len(updated)))


def check_and_update(match, paper, session, dryrun=False):
    """
    Check if a new version of a paper needs to overwrite an old one.

    This would be much more efficient if there was a last_modified date in ADS.

    Returns the id if anything was updated.
    """
    # Check single values:
    # bibcode, title, abstract, doi, pub_opeanccess, refered.
    updated_papers=[]

    #logger.debug('Updating title, bibcode, abstract, pub etc for {}: {}'.format(match.bibcode, match.title))
    for attrib in ['title', 'bibcode', 'abstract', 'pub_openaccess',
                   'refereed', 'doi', 'pubdate']:
        if getattr(match, attrib) != getattr(paper, attrib):
            logger.debug('Update required for {} in {}'.format(attrib, match.bibcode))
            logger.debug('old was {}; new is {}'.format(getattr(match, attrib), getattr(paper, attrib)))
            if not dryrun:
                setattr(match, attrib, getattr(paper, attrib))
            updated_papers.append(match.bibcode)

    if (set([i.identifier for i in paper.identifiers]) !=
        set([i.identifier for i in match.identifiers])):
        logger.debug('Update required for identifiers in {}'.format(match.bibcode))
        if not dryrun:
            for i in match.identifiers:
                session.delete(i)
            match.identifiers = paper.identifiers.copy()
        updated_papers.append(match.bibcode)

    if (set([i.keyword for i in paper.keywords]) !=
        set([i.keyword for i in match.keywords])):
        logger.debug('Update required for keywords in {}'.format(match.bibcode))
        if not dryrun:
            for i in match.keywords:
                session.delete(i)
            match.keywords = paper.keywords.copy()

        updated_papers.append(match.bibcode)

    if (set([i.property for i in paper.properties]) !=
        set([i.property for i in match.properties])):
        logger.debug('Update required for properties in {}'.format(match.bibcode))
        if not dryrun:
            for i in match.properties:
                session.delete(i)
            match.properties = paper.properties.copy()

        updated_papers.append('properties')

    if (set([(i.position_,i.author,i.affiliation) for i in paper.authors]) !=
        set([(i.position_,i.author,i.affiliation) for i in match.authors])):
        logger.debug('Update required for authors in {}'.format(match.bibcode))
        if not dryrun:
            for i in match.authors:
                session.delete(i)
            match.authors = paper.authors.copy()
        updated_papers.append('authors')

    # Searches: this should include all, not replace
    if (set([i.id for i in paper.searches]) !=
        set([i.id for i in match.searches])):
        logger.debug('Update required for searches in {}'.format(match.bibcode))
        if not dryrun:
            match.searches += paper.searches
    if not dryrun:
        session.flush()
        session.commit()
        session.flush()


    return set(updated_papers)
    ""


def check_if_paper_in_db(paper, session):

    # If bibcode matches, then definitely in
    try:
        match = session.query(Paper).filter(Paper.bibcode==paper.bibcode).one()
    except sqlalchemy.orm.exc.NoResultFound:
        # Check all identifiers
        try:
            match = session.query(Paper).join(Identifier).filter(
                Identifier.identifier.in_([i.identifier for i in paper.identifiers])
            ).one()
        except sqlalchemy.orm.exc.NoResultFound:
            match = None
    # Add check for multiple results? Don't know if this ever can
    # happen?
    if match:
        logger.debug('{}: {} already in DB'.format(paper.bibcode,paper.title))
    return match



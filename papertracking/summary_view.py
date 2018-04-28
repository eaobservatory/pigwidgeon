# Search for summarys of comments in database.
from sqlalchemy import func
import datetime
from papertracking.db import Paper, Identifier, Author, Search, PaperType, PaperTypeValue, \
    Comment, InfoSection, InfoSectionValue, InfoSublist
from io import BytesIO
from papertracking.util import create_session
from collections import OrderedDict
from astropy.table import Table, Column
import logging
from flask import send_file
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
import numpy  as np
import base64
import copy
logger = logging.getLogger(__name__)

def create_summary_by_papertype(session, searchid, username=None, papertypes_to_query=None,
                                infosections_to_query=None, paperarguments=None):
    """
    Get a summary of papers classified by infosections, based on comments in the DB.

    searchid: integer, id of search to check

    username: str if not None, then only look at records by that
              username. Otherwise default to most recent comment per
              paper.

    infosections_to_query: if not None, then list of infosection IDs:
                           only provide classifications for those
                           infosections.

    paperarguments: dictionary of paperarguments. refereed, startdate, enddate

    returns dictionaries of results by name
    """

    if not session:
        session = create_session()

    # Get all papertypes that we care about
    papertypes = session.query(PaperType).filter(Search.id==searchid).order_by(PaperType.position_).all()
    if papertypes_to_query:
        papertypes = [p for p in papertypes if p.id in papertypes_to_query]

    # ensure arguments are in correct format:
    if paperarguments:
        refereed = paperarguments.get('refereed', None)
        print(refereed, type(refereed))
        day = datetime.timedelta(days=1)
        start = end = None
        if 'startdate' in paperarguments:
            start = datetime.datetime.strptime(paperarguments['startdate'], '%Y-%m') - day
        if 'enddate'  in paperarguments:
            end = datetime.datetime.strptime(paperarguments['enddate'], '%Y-%m') + day


    # Get list of infosections, sorted by position_.
    if infosections_to_query:
        infosections = session.query(InfoSection).filter(InfoSection.search_id==searchid).\
                               filter(InfoSection.id.in_(infosections_to_query)).all()
    else:
        infosections = session.query(InfoSection).filter(InfoSection.search_id==searchid).all()
    infosections.sort(key = lambda x: x.position_)

    results = OrderedDict()
    commentquery = session.query(Comment).filter(Search.id==int(searchid))
    if username:
        commentquery = commentquery.filter(Comment.username==username)
        idlist = session.query(Comment.id, func.max(Comment.datetime)).filter(Comment.search_id==searchid).\
                               filter(Comment.username==username).group_by(Comment.paper_id).all()
        idlist = [i[0] for i in idlist]

    else:
        #raise NotImplementedError('No username not yet supported!')
        #idlist = session.query(func.max(Comment.datetime)).group_by(Comment.paper_id, Comment.search_id)
        idlist = session.query(Comment.id, func.max(Comment.datetime)).filter(Comment.search_id==searchid).\
                                      group_by(Comment.paper_id).all()
        idlist = [i[0] for i in idlist]

    # Do paper querys
    # Get matching set of papers whether commented on or not.
    all_papers = session.query(Paper).filter(Paper.searches.any(Search.id==searchid))
    if paperarguments:
        commentquery = commentquery.join(Paper)
        if refereed is not None:
            print("refereed is being checked", refereed, type(refereed))
            commentquery = commentquery.filter(Paper.refereed == refereed)
            all_papers  = all_papers.filter(Paper.refereed == refereed)
        if start:
            commentquery = commentquery.filter(Paper.pubdate >= start)
            all_papers = all_papers.filter(Paper.pubdate >= start)
        if end:
            commentquery = commentquery.filter(Paper.pubdate <= end)
            all_papers = all_papers.filter(Paper.pubdate <= end)

    full_paper_set = all_papers.all()
    results['matching_papers'] = set(full_paper_set)

    # Ensure we are only getting the latest comment (possibly by that username).
    #commentquery = commentquery.filter(Comment.id.in_(idlist))
    comments = commentquery.all()
    comments = [c for c in comments if c.id in idlist and c.paper is not None]
    commented_papers = set([c.paper for c in comments])

    results['commented_papers'] = commented_papers

    results['missing_papers'] = results['matching_papers'].difference(results['commented_papers'])




    # Go through all results
    for p in papertypes:

        resdict = OrderedDict()
        # find all comments for that.

        paper_category_query = commentquery.filter(Comment.papertypevalues.any(PaperTypeValue.papertype_id==p.id))

        # Get results
        comments = paper_category_query.order_by(Comment.paper_id).all()
        comments = [c for c in comments if c.id in idlist and c.paper is not None]

        papers = list(set([i.paper for i in comments]))
        if len(papers) != len(comments):
            print('Warning: multiple comments being returned for a single paper! programming error!')

            return papers, comments

        resdict['matching_papers'] = set(papers)
        papercount = len(resdict['matching_papers'])
        print('{}: {} papers'.format(p.name_, papercount))

        # Now get more information about each one.
        # 1. find all papers that are have multiple paper types.
        multiple_papertypes = [c for c in comments if len(c.papertypevalues) > 1]
        multiple_papertypes = list(set([c.paper for c in multiple_papertypes]))
        if len(multiple_papertypes) > 0:
            logger.info('\t{} papers have been assigned multiple papertypes: ids are {}'.format(
                len(multiple_papertypes), ', '.join([str(p.id) for p in multiple_papertypes])))
            resdict['multiple_papertypes'] = multiple_papertypes


        # Go through each InfoSection
        if papercount > 0:
            for i in infosections:
                print('\t{}'.format(i.name_))
                resdict[i.name_] = OrderedDict()
                if i.type_ == 1:
                    logger.info('\t{}'.format(i.name_))
                    possible_values = i.sublists

                    for j in possible_values:
                        # j is an InfoSublist
                        matches = [d for c in comments for d in c.infosectionvalues if d.info_sublist_id == j.id]
                        if len(matches) > 0:
                            #logger.info('\t\t{}: {}'.format(j.named, len(matches)))
                            print('\t\t{}: {}'.format(j.named, len(matches)))
                        resdict[i.name_][j.named] = [m.comment.paper for m in matches]
                if i.type_ == 3:
                    # If its a short list, then keep track of all entries.
                    matches = [d for c in comments for d in c.infosectionvalues if d.infosection.id == i.id]

                    # Turn into a flattened unique list.
                    texts = set([flatcode.strip() for m in matches
                                                  for flatcode in m.entered_text.split('\n')
                                                  if m.entered_text])

                    # Find sets of papers for each entry
                    for t in texts:
                        matching_papers = set([c.paper for c in comments
                                                      for isvalue in c.infosectionvalues if isvalue.entered_text
                                                      for entry in isvalue.entered_text.split('\n')
                                                      if t in entry])
                        resdict[i.name_][t] = matching_papers
                        if len(matching_papers) > 0:
                            print('\t\t{}: {}'.format(t, len(matching_papers)))
                if i.type_ == 2:
                    # For free form notes sections, no analysis possible.
                    resdict.pop(i.name_)
                    pass



        results[p.name_] = resdict


    # Now create summary tables
    overallsummary = create_summary_table_dict(results, categories=[p.name_ for p in papertypes])
    summarytables_specific = dict()
    for p in papertypes:
        if p.name_ in results:
            papers = results[p.name_]['matching_papers']
            summarytables_specific[p.name_] = {}
            for i in infosections:
                if i.name_ in results[p.name_]:
                    table = create_summary_table_dict(results[p.name_][i.name_], papers=papers)
                    summarytables_specific[p.name_][i.name_] = table

    return results, overallsummary, summarytables_specific


def create_summary_table_dict(results, papers=None, categories=None):
    """
    Create an astropy.table object summarising information.

    Requires results dictionary in format produced by create_summary_by_papertype
    """


    if not papers:
        papers = list(results['matching_papers'])

    # Authors is occasionally an empty string, so trap that case
    rows = [[paper.bibcode,
             (paper.authors[0:] + ['None'])[0],
             paper.pubdate,
             paper.title,
             paper.refereed,
             paper.id] for paper in papers]
    summarytable = Table(rows=rows,
                         names=['Bibcode', 'First Author', 'Pub. Date', 'Title', 'Refereed?', 'id'])

    if not categories:
        categories = list(results.keys())

    for category in categories:
        if category not in ['commented_papers', 'missing_papers', 'matching_papers']:
            if 'matching_papers' in results[category]:
                matching_papers = results[category]['matching_papers']
            else:
                matching_papers = results[category]
            matches = [True if p in matching_papers else False  for p in papers]
            col = Column(data=matches, name=category, dtype=bool)
            summarytable.add_column(col)
    return summarytable


def create_summary_table_plots(results):


#    results.pop('commented_papers')
#    results.pop('missing_papers')
#    results.pop('matching_papers')
    keywords_to_skip = ['commented_papers', 'missing_papers', 'matching_papers', 'multiple_papertypes']
    types = list(results.keys())
    [types.remove(i) for i in keywords_to_skip if i in types]
    fig = Figure()
    fig.patch.set_visible(False)
    ax = fig.add_subplot(111)
    values = [len(results[ptype]['matching_papers']) for ptype in types if ptype not in keywords_to_skip]
    ax.bar(np.arange(len(types)), values)

    ax.set_xticks(np.arange(len(types)))
    ax.set_xticklabels(types, fontdict={'rotation':45.0, 'ha':'right'})
    fig.tight_layout()
    canvas = FigureCanvas(fig)
    img = BytesIO()
    canvas.print_png(img)
    img.seek(0)

    overallim = base64.b64encode(img.getvalue()).decode()

    # Individual images:
    imagedict = OrderedDict()
    for ptype in types:
        info = results[ptype]
        imagedict[ptype] = OrderedDict()
        for k in info.keys():
            if k not in keywords_to_skip:
                bars = list(info[k].keys())
                values = [len(info[k][i]) for i in bars]
                fig = Figure()
                fig.patch.set_visible(False)
                ax = fig.add_subplot(111)
                ax.set_title(k)
                ax.bar(np.arange(len(bars)), values)
                ax.set_xticks(np.arange(len(bars)))
                ax.set_xticklabels(bars, fontdict={'rotation':45.0, 'ha':'right'})
                fig.tight_layout()
                canvas = FigureCanvas(fig)
                img = BytesIO()
                canvas.print_png(img)
                img.seek(0)

                imagedict[ptype][k] = base64.b64encode(img.getvalue()).decode()

    return overallim, imagedict



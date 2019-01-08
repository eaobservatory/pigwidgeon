# Search for summarys of comments in database.
from sqlalchemy import func, and_
from sqlalchemy.orm import subqueryload
import datetime
from .db import Paper, Identifier, Author, Search, PaperType, PaperTypeValue, \
    Comment, InfoSection, InfoSectionValue, InfoSublist
from io import BytesIO
from .util import create_session
from collections import OrderedDict
from astropy.table import Table, Column

import logging
from flask import send_file, url_for


import numpy  as np
import base64


logger = logging.getLogger(__name__)



import pandas as pd

def fixup_summarytable(table, searchid):
    if table is not None:
        table = table.reset_index()
        cols = table.columns.droplevel(1)
        cols = ['' if i=='commentid' else i for i in cols]
        typecols = table.columns.droplevel(0)
        newcols = cols + typecols
        table.columns = newcols
        table = table.rename({'paper_id':'Paper'}, axis=1)
        table['Paper'] = ['<a href="{}">{}</a>'.format(
            url_for('auth.paper_info_page', paperid=i, searchid=searchid), i)
                          for i in table['Paper'] ]
    return table

logger.setLevel('DEBUG')
def create_summary_by_papertype(dbsession, searchid, username=None, papertypes_to_query=None,
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

    if not dbsession:
        dbsession = create_session()

    # Get all papertypes that we care about
    papertypes = dbsession.query(PaperType).filter(Search.id==searchid).order_by(PaperType.position_).all()
    if papertypes_to_query:
        papertypes = [p for p in papertypes if p.id in papertypes_to_query]
    # ensure arguments are in correct format:
    if paperarguments:
        refereed = paperarguments.get('refereed', None)
        day = datetime.timedelta(days=1)
        start = end = None
        startdate = paperarguments.get('startdate', None)
        enddate = paperarguments.get('enddate', None)
        if startdate and startdate != "":
            start = datetime.datetime.strptime(paperarguments['startdate'], '%Y-%m') - day
        if enddate  and enddate != "":
            end = datetime.datetime.strptime(paperarguments['enddate'], '%Y-%m') + day


    # Get list of infosections, sorted by position_.
    infosections = dbsession.query(InfoSection).options(subqueryload(InfoSection.sublists)).filter(InfoSection.search_id==searchid)

    if infosections_to_query:
        infosections = infosections.filter(InfoSection.id.in_(infosections_to_query))

    infosections = infosections.all()
    infosections.sort(key = lambda x: x.position_)

    results = OrderedDict()

    # Create a comment query, and enuser that infosectionvalues and papertypevalues are eagerly loaded.
    commentquery = dbsession.query(Comment, Paper, Author.author).filter(Search.id==int(searchid))
    commentquery = commentquery.join(Paper, Comment.paper_id==Paper.id)
    commentquery = commentquery.join(Author, Comment.paper_id==Author.paper_id).filter(Author.position_==0)
    commentquery = commentquery.group_by(Comment.id)
    commentquery = commentquery.options(subqueryload(Comment.infosectionvalues)).options(
        subqueryload(Comment.papertypevalues))

    # Ensure that we have added in first author to avoid querying it

    # Only match the most recent comment per paper, optionally only by a specific username.
    recentcommentquery = dbsession.query(func.max(Comment.id).label('id')).\
                             filter(Comment.search_id==searchid).\
                             group_by(Comment.paper_id)
    if username:
        recentcommentquery = recentcommentquery.filter(Comment.username==username)
    recentcommentquery = recentcommentquery.subquery('t')
    commentquery = commentquery.filter(and_(Comment.id==recentcommentquery.c.id))


    # Do paper querys
    # Get matching set of papers whether commented on or not.
    all_papers = dbsession.query(Paper, Author.author).outerjoin(Author, Paper.id==Author.paper_id).filter(Author.position_==0).filter(Paper.searches.any(Search.id==searchid))
    #all_papers = dbsession.query(Paper).filter(Paper.searches.any(Search.id==searchid))
    if paperarguments:
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
    fullcomments = commentquery.all()
    #comments = [c for c in comments if c.id in idlist and c.paper is not None]
    commented_papers = set([c.Paper for c in fullcomments])

    results['commented_papers'] = fullcomments


    matching_comments_onlypapers = set([p.Paper for p in fullcomments])
    missing_papers  = [p for p in full_paper_set if p.Paper not in matching_comments_onlypapers]


    # Creating pandas stuff.

    header = ['commentid', 'paper_id', 'username', 'firstauthor', 'title', 'pubdate', 'refereed', 'papertype', 'papertypeid', 'sectionnamed', 'sectionid', 'entered_text', 'sublist_id','sublist_name']
    results = []
    for c in fullcomments:
        paperinfo = [c.Comment.id, c.Comment.paper_id, c.Comment.username, c.author, c.Paper.title, c.Paper.pubdate, c.Paper.refereed]
        for p in c.Comment.papertypevalues:
            row = paperinfo + [p.papertype.name_, p.papertype_id]
            for i in c.Comment.infosectionvalues:
                if i.infosection.type_ == 3 and i.entered_text is not None:
                    texts = i.entered_text.split('\n')
                    for t in texts:
                        if t is not None and t != '':
                            results += [row + [i.infosection.name_, i.infosection.id, t, getattr(i.infosublist, 'id', None), getattr(i.infosublist, 'named', None)]]
                else:
                    results += [row + [i.infosection.name_, i.infosection.id, i.entered_text, getattr(i.infosublist, 'id', None), getattr(i.infosublist, 'named', None)]]



    res = pd.DataFrame(data=results, columns=header)
    res['pubdate'] = pd.to_datetime(res['pubdate'])

    papertypecat = pd.Categorical([i.name_ for i in papertypes], ordered=True)

    generalcolumns = ['commentid','paper_id', 'username', 'firstauthor', 'title', 'pubdate', 'refereed']
    pivotgeneralcolumns = ['paper_id','firstauthor','title', 'refereed', 'pubdate', 'username']
    papertypesub = res[generalcolumns + ['papertype']].drop_duplicates()
    overallsummary = pd.DataFrame(papertypesub['papertype'].value_counts().reindex(papertypecat, fill_value=0).rename('counts'))

    overallsummarytable = papertypesub.pivot_table(index=pivotgeneralcolumns,
                                            values=['commentid'],
                                            aggfunc='count',
                                            columns=['papertype'],
                                            fill_value=0)


    ptypedict = OrderedDict()

    # Go through each papertype.
    for ptype in papertypecat:
        infosectdict = OrderedDict()
        for infosec in infosections:
            if infosec.type_ != 2:
                name = infosec.name_
                subtable = res[(res['sectionnamed']==name)&(res['papertype']==ptype)]
                if len(subtable) > 0:
                    if infosec.type_ == 3:
                        subtable = subtable[generalcolumns + ['sectionnamed', 'entered_text']].drop_duplicates()
                        summary = subtable['entered_text'].value_counts()
                        summarytable = subtable.pivot_table(index=pivotgeneralcolumns,
                                                            values=['commentid'],
                                                            aggfunc='count',
                                                            columns=['entered_text'],
                                                            fill_value=0)


                    else:
                        sublist = sorted(infosec.sublists, key=lambda x: x.position_)
                        cat = pd.Categorical([i.named for i in sublist], ordered=True)
                        subtable = subtable[generalcolumns + ['sectionnamed', 'sublist_name']].drop_duplicates()

                        summary = subtable['sublist_name'].value_counts().reindex(cat, fill_value=0)
                        summarytable = subtable.pivot_table(index=pivotgeneralcolumns,
                                                            values=['commentid'],
                                                            aggfunc='count',
                                                            columns=['sublist_name'],
                                                            fill_value=0)

                    infosectdict[name] = (pd.DataFrame(summary.rename('counts')), summarytable)
                else:
                    infosectdict[name] = (None, None)
        ptypedict[ptype] = infosectdict


    return missing_papers, res, overallsummary,overallsummarytable, ptypedict


def create_summary_table_dict(results, matches=None, categories=None):
    """
    Create an astropy.table object summarising information.

    Requires results dictionary in format produced by create_summary_by_papertype
    """


    if not matches:
        matches = list(results['matching_papers'])

    # Authors is occasionally an empty string, so trap that case
    rows = [[m.Paper.bibcode,
             m.author,
             m.Paper.pubdate,
             m.Paper.title,
             m.Paper.refereed,
             m.Paper.id] for m in matches]
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
            finalmatches = [True if p in matching_papers else False  for p in matches]
            col = Column(data=finalmatches, name=category, dtype=bool)
            summarytable.add_column(col)
    return summarytable

def create_mpl_barchart(series, title=False):
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
    fig = Figure()
    fig.patch.set_visible(False)
    ax = fig.add_subplot(111)
    labels = series.index.tolist()
    ax.bar(np.arange(len(labels)), list(series.counts))
    ax.set_xticks(np.arange(len(labels)))
    ax.set_xticklabels(labels, fontdict={'rotation':45.0, 'ha': 'right'})
    if title:
        ax.set_title(title)
    fig.tight_layout()
    canvas = FigureCanvas(fig)
    img = BytesIO()
    canvas.print_png(img)
    img.seek(0)
    image = base64.b64encode(img.getvalue()).decode()
    return image



def create_summary_plots_mpl(overallsummary, ptypedict):
    keys = ['overall']
    figs = []
    figs.append(create_mpl_barchart(overallsummary))

    for ptype, dicts in ptypedict.items():
        for isection, (summary, table) in dicts.items():
            if summary is not None and len(summary) > 0:
                title = '{}---{}'.format(ptype, isection)
                figs.append(create_mpl_barchart(summary, title=title))
                keys.append(title)

    return dict(zip(keys, figs))



def create_summary_table_plots(results):

    from matplotlib.figure import Figure
    from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
    start = datetime.datetime.now()

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

    logger.debug('Overallimage %s', (datetime.datetime.now() - start))

    p = figure(x_range=types, title=None, height=400, width=800, tools="save")
    datadict=dict(types=types, counts=values, labels=[i if i > 0 else '' for i in values])
    data = ColumnDataSource(data=datadict)
    labels = LabelSet(x='types', y='counts',
                      text='labels',
                      level='glyph', render_mode='canvas', source=data,
                      y_offset=0, text_align='center', text_baseline='bottom')
    p.vbar(x='types', top='counts', width=0.9, source=data)
    p.add_layout(labels)
    p.xaxis.major_label_orientation = np.pi/4
    p.xaxis.major_label_text_font_style='bold'

    p.border_fill_color = None
    p.y_range.start = 0
    p.min_border_left=80
    p.outline_line_color = "black"
    p.xgrid.grid_line_color = None
    bokehplot = components(p)

    logger.debug('Bokehimage %s', (datetime.datetime.now() - start))
    # Individual images:
    imagedict = OrderedDict()
    for ptype in types:
        info = results[ptype]
        imagedict[ptype] = OrderedDict()
        for k in info.keys():
            if k not in keywords_to_skip:
                bars = list(info[k].keys())
                values = [len(info[k][i]) for i in bars]
                ax.clear()
                ax.set_title(k)
                ax.bar(np.arange(len(bars)), values)
                ax.set_xticks(np.arange(len(bars)))
                ax.set_xticklabels(bars, fontdict={'rotation':45.0, 'ha':'right'})
                fig.tight_layout()
                canvas = FigureCanvas(fig)
                img = BytesIO()
                logger.debug('BEFORE PRINT PNG: %s:  %s', ptype, datetime.datetime.now() - start)
                canvas.print_png(img)
                img.seek(0)

                imagedict[ptype][k] = base64.b64encode(img.getvalue()).decode()
                logger.debug('%s:  %s', ptype, datetime.datetime.now() - start)
    return overallim, imagedict, bokehplot



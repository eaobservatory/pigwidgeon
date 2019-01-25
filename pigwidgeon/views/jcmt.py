# JCMT specific pages.
import numpy as np
import pandas as pd
import base64
from io import BytesIO
from sqlalchemy import func, and_

from flask import Blueprint, url_for, render_template, send_file, request


from ..auth.views import login_required
from ..util import  create_session
from ..db import Search, Paper, Comment, PaperType, PaperTypeValue, Author, InfoSectionValue, \
    InfoSublist, InfoSection

from ..summary_view import create_summary_by_papertype

jcmt = Blueprint('jcmt', __name__)
searchid = 1

JCMT_PUBS = ['JCMT Science Paper','JCMT Theory Paper']
UNKNOWN_PUBS = ['Unknown']
def get_jcmt_paper_query(pigsession):

    # Get the most recent comment for each paper
    recentcommentquery = pigsession.query(func.max(Comment.id).label('id')).\
                             filter(Comment.search_id==searchid).\
                             group_by(Comment.paper_id)

    recentcommentquery = recentcommentquery.subquery('t')

    papertypes = pigsession.query(PaperType).filter(Search.id==searchid).filter(
        PaperType.name_.in_(JCMT_PUBS)).all()

    paperquery = pigsession.query(Paper).join(Comment, Paper.id==Comment.paper_id)\
                                        .filter(and_(Comment.id==recentcommentquery.c.id))\
                                        .filter(Comment.papertypevalues.any(
                                            PaperTypeValue.papertype_id.in_([i.id for i in papertypes])))\
                                        .filter(Paper.refereed==True)
    query = paperquery.join(Author, Paper.id==Author.paper_id)\
                      .add_column(Author.author)\
                      .add_column(Author.affiliation)\
                      .add_column(Author.position_)
    query = query.join(InfoSectionValue, Comment.id==InfoSectionValue.comment_id)
    query = query.join(InfoSection, InfoSectionValue.info_section_id==InfoSection.id)
    query = query.join(InfoSublist, InfoSublist.id==InfoSectionValue.info_sublist_id)
    query = query.add_column(InfoSection.name_.label('section'))
    query = query.add_column(InfoSublist.named.label('section_value'))
    query = query.add_column(InfoSectionValue.entered_text.label('section_text'))

    return query


def get_unknown_papers(pigsession):
    recentcommentquery = pigsession.query(func.max(Comment.id).label('id')).\
                             filter(Comment.search_id==searchid).\
                             group_by(Comment.paper_id)

    recentcommentquery = recentcommentquery.subquery('t')

    papertypes = pigsession.query(PaperType).filter(Search.id==searchid).filter(
        PaperType.name_.in_(UNKNOWN_PUBS)).all()

    paperquery = pigsession.query(Paper).join(Comment, Paper.id==Comment.paper_id)\
                                        .filter(and_(Comment.id==recentcommentquery.c.id))\
                                        .filter(Comment.papertypevalues.any(
                                            PaperTypeValue.papertype_id.in_([i.id for i in papertypes])))\
                                        .filter(Paper.refereed==True)
    return paperquery.all()

def get_unchecked_papers(pigsession):
    comments = pigsession.query(Comment.paper_id)
    missedpapers = pigsession.query(Paper).filter(Search.id==searchid)\
                                          .filter(Paper.id.notin_(comments))\
                                          .filter(Paper.refereed==True)

    return missedpapers.all()

@jcmt.route('/jcmt/overview')
#@login_required
def overview():

    pigsession = create_session()
    search = pigsession.query(Search).filter(Search.id==searchid).one()

    # Get missing paper counts
    missedpapers = get_unchecked_papers(pigsession)
    unknownpapers = get_unknown_papers(pigsession)

    data=[[i.id, i.pubdate.year] for i in missedpapers] + [[i.id, i.pubdate.year] for i in unknownpapers]
    missedpapers = pd.DataFrame(data=data,
                                columns=['paper_id', 'year']).drop_duplicates()

    missed = pd.DataFrame(missedpapers['year'].value_counts().rename('Unread or Unknown Papers').sort_index())


    return render_template('jcmt/jcmt_summary.html', search=search,  missed=missed)



@jcmt.route('/jcmt/images/publications')
def jcmt_publication_graph():

    from matplotlib.figure import Figure
    from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas


    startdate = request.args.get('startdate', None)
    enddate  = request.args.get('enddate', None)
    breakdown = request.args.get('breakdown', None)

    pigsession = create_session()
    search =  pigsession.query(Search).filter(Search.id==searchid).one()
    papertypes = [i.id for i in search.papertypes if i.name_ in ['JCMT Science Paper', 'JCMT Theory Paper']]

    missing_papers, res, overallsummary, overallsummarytable, ptypedict = create_summary_by_papertype(
        pigsession, searchid, paperarguments={'refereed':True, 'startdate': startdate, 'enddate': enddate},
        papertypes_to_query=papertypes)
    res['year'] = [i.year for i in res['pubdate']]
    res = res[res['papertype'].isin(JCMT_PUBS)]

    res['sublist_name'][res['sublist_name']=='Solar System (Comets, planets and satellites etc.)']='Solar System'
    res['sublist_name'][res['sublist_name']=='Debris disks and circumstellar matter']='Debris disks etc.'
    df = res[['papertype', 'sectionnamed', 'year', 'sublist_name', 'paper_id']]

    if breakdown is None:
        df = df[['paper_id', 'year']].drop_duplicates()
        results = df.groupby('year').agg({'paper_id': lambda x: len(set(x))})
        title = 'Year'
        cmap = None
        legend = None
    else:
        df = df[df['sectionnamed'] == breakdown][['paper_id', 'year', 'sublist_name']].drop_duplicates()
        results = df.groupby(['sublist_name', 'year']).agg({'paper_id': lambda x: len(set(x))}).unstack()
        title = breakdown
        cmap = 'viridis'
        legend = True
        labels = results.columns.levels[1].values

    #paperquery = get_jcmt_paper_query(pigsession)
    #papers = paperquery.all()
    #data = [[i.Paper.id, i.Paper.pubdate.year] for i in paperquery]
    #df = pd.DataFrame(data=data, columns=['paper_id', 'year'])
    #df = df.drop_duplicates()

    fig = Figure()
    fig.patch.set_visible(False)
    ax = fig.add_subplot(111)

    results.plot.bar(legend=legend, ax=ax, cmap=cmap)
    ax.set_title('JCMT Publications by {}'.format(title))
    ax.set_xlabel('')
    ax.set_ylabel('Publication Count')
    ax.yaxis.grid(which='major', linestyle='--', alpha=0.5)
    ax.set_axisbelow(True)
    if legend:
       handles, labelsold = ax.get_legend_handles_labels()
       leg = ax.legend(title='Year', handles=handles, labels=list(labels))#, bbox_to_anchor=(1, 1), loc='upper left')
    #bbox = fig.get_tightbbox(FigureCanvas(fig).get_renderer(), bbox_extra_artists=(leg,))
    #print(bbox)
    size = fig.get_size_inches()
    fig.set_size_inches([size[0] + 4, size[1] + 2])
    fig.tight_layout()
    canvas = FigureCanvas(fig)
    img = BytesIO()
    canvas.print_png(img)
    img.seek(0)

    return send_file(img, mimetype='image/png')

    # search =  pigsession.query(Search).filter(Search.id==searchid).one()
    # papertypes = [i.id for i in search.papertypes if i.name_ in ['JCMT Science Paper', 'JCMT Theory Paper']]
    # missing_papers, res, overallsummary, overallsummarytable, ptypedict = create_summary_by_papertype(pigsession,
    #                                                                                                   searchid,
    #                                                                                                   username=None,
    #                                 papertypes_to_query=papertypes,
    #                                 paperarguments = {'refereed': True, 'startdate': startdate,
    #                                               'enddate': enddate})

    # res['year'] = [i.year for i in res['pubdate']]
    # results = res[['paper_id', 'year']].drop_duplicates()
    # results = results.groupby('year').agg({'paper_id': lambda x: len(set(x))})
    # fig = Figure()
    # fig.patch.set_visible(False)
    # ax = fig.add_subplot(111)
    # results.plot.bar(legend=False, ax=ax)
    # ax.set_title('JCMT Publications')
    # fig.tight_layout()
    # canvas = FigureCanvas(fig)
    # img = BytesIO()
    # canvas.print_png(img)
    # img.seek(0)

    # return send_file(img, mimetype='image/png')

#import flask
#@jcmt.route('/jcmt/dashboard')
#def render_jcmt_dashboard():
#    return flask.redirect('/dash')


from __future__ import absolute_import, division, print_function

from docopt import docopt
import functools
import os
from flask import Flask, redirect, url_for, render_template, request, session
import flask

from sqlalchemy.orm import aliased
from sqlalchemy import  func


import werkzeug.routing
from werkzeug import MultiDict

import datetime

from ..db import Paper, Search, PaperType, InfoSection, InfoSublist, \
    Base, Comment, InfoSectionValue, Identifier, PaperTypeValue, Author
from ..search import create_search_from_request, create_comment_from_request
from ..paper import get_paper_info
from ..util import  create_session, isType

import numpy as np
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas

from flask import request, render_template, render_template_string, flash, redirect, \
    url_for, Blueprint, g
from flask.ext.login import current_user, login_user, \
    logout_user, login_required
from papertracking import login_manager, ldap_manager

from papertracking.auth.user import User

from flask_ldap3_login.forms import LDAPLoginForm

from papertracking import app, users

auth = Blueprint('auth', __name__)

from collections import OrderedDict, namedtuple



def get_commentsearch_info(searchquery, search):
    res = []
    if 'papertype' in searchquery:
        ptypeids = [int(i) for i in searchquery['papertype']]
        ptypeids.sort()
        ptypenames = [i.name_ for i in search.papertypes if i.id in ptypeids]
        res.append(('papertype', ptypenames))
    infosections = [k for k in searchquery.keys() if k.startswith('infosection')]
    infosections.sort()
    for iskey in infosections:
        if searchquery[iskey] and searchquery[iskey] != [] and searchquery[iskey] != ['']:
            isid = int(iskey.split('_')[-1])
            infosection = [i for i in search.infosections if i.id==isid][0]
            if infosection.type_==isType.NOTES:
                res.append((infosection.name_, searchquery[iskey][0]))
            elif infosection.type_==isType.TEXTPERLINE:
                values = searchquery[iskey][0].split('\n')
                values = [v.strip() for v in values]
                res.append((infosection.name_, values))
            else:
                sublistids = [int(i) for i in searchquery[iskey]]
                sublistids.sort()
                sublistnames = [i.named for i in infosection.sublists if i.id in sublistids]
                res.append((infosection.name_, sublistnames))
    return OrderedDict(res)



dbsession = create_session()
@login_manager.user_loader
def load_user(id):
    if id in users:
        return users[id]
    return None

@ldap_manager.save_user
def save_user(dn, username, data, memberships):
    user = User(dn, username, data)
    users[dn] = user
    return user


@auth.before_request
def get_current_user():
    g.user = current_user

@auth.route('/')
@auth.route('/front_page')
def front_page():
    # Get all currently setup searches.
    searches = dbsession.query(Search).all()
    return render_template('frontpage.html', searches=searches)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    template = """
        {{ get_flashed_messages() }}
    {{ form.errors }}
    <form method="POST">
        <label>Username{{ form.username() }}</label>
        <label>Password{{ form.password() }}</label>
        {{ form.submit() }}
        {{ form.hidden_tag() }}
    </form>
    """
    form = LDAPLoginForm()

    if form.validate_on_submit():

        login_user(form.user)
        flask.flash('Logged in successful')
        next = flask.request.args.get('next')

        if not is_safe_url(next):
            return flask.abort(400)


        return redirect(next or url_for('auth.front_page'))

    return render_template_string(template, form=form)


@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.front_page'))


@auth.route('/search/<searchid>/paper-comments/<paperid>')
def paper_comments_info_page(paperid, searchid):
    search, paper = get_paper_info(paperid,searchid, dbsession)

    # Get all comments on a specific paper.
    comments = dbsession.query(Comment).filter_by(search_id=searchid, paper_id=paperid).all()

    if hasattr(current_user, 'username'):
         currentusers = dbsession.query(Comment).filter_by(search_id=searchid,
                                    paper_id=paperid,
                                    username=current_user.username
         ).order_by(Comment.datetime.desc()).all()
    else:
        currentusers = None
    if 'comment_query' in session:
        print('paper comments session comment_query', session['comment_query'])
        query = create_comment_search(dbsession, searchid, MultiDict(session['comment_query']))
        allcomments = query.order_by(Comment.paper_id).all()
        papers = list(set([i.paper.id for i in allcomments if i.paper is not None]))
        papers.sort()
        try:
            previd = [i for i in papers if i < int(paperid)][-1]
        except IndexError:
            previd = None
        try:
            nextid = [i for i in papers if i > int(paperid)][0]
        except IndexError:
            nextid = None
        length = len(papers)
        if paper.id in papers:
            position = papers.index(paper.id) + 1
        else:
            position = None
        paper_position = (nextid, previd, length, position)
        searchquery = session['comment_query']
        commentsearchinfo = get_commentsearch_info(searchquery, search)
    else:
        paper_position = None
        searchquery = None
        commentsearchinfo = None
    return render_template('papercommentview.html', paper=paper, searchquery=searchquery,
                           search=search, comments=comments, current=currentusers,
                           paper_position=paper_position,commentsearchinfo=commentsearchinfo)

@auth.route('/search/<searchid>/paper/<paperid>')
def paper_info_page(paperid, searchid):
    search, paper = get_paper_info(paperid,searchid, dbsession)
    comments = dbsession.query(Comment).filter_by(search_id=searchid, paper_id=paperid).all()
    if hasattr(current_user, 'username'):
         currentusers = dbsession.query(Comment).filter_by(search_id=searchid,
                                    paper_id=paperid,
                                    username=current_user.username
         ).order_by(Comment.datetime.desc()).all()
    else:
        currentusers = None

    # If a search is present in the flask session (paper_query
    # keyword), then also get the next paper, previous paper and the
    # number of papers and this papers location in list?
    if 'paper_query' in session:
        query = create_papersearch_query(dbsession, searchid, **session['paper_query'])

        # Find next page
        try:
            nextid = query.order_by(Paper.id).filter(Paper.id > int(paperid)).first().id
        except AttributeError:
            nextid = None
        try:
            previd = query.order_by(Paper.id.desc()).filter(Paper.id < int(paperid)).first().id
        except AttributeError:
            previd = None

        fulllist = query.order_by(Paper.id).all()
        length = len(fulllist)
        if paper in fulllist:
            position = fulllist.index(paper) + 1
        else:
            position = None
        paper_position = (nextid, previd, length, position)
        searchquery = session['paper_query']
    else:
        paper_position = (None, None, None, None)
        searchquery = {}

    return render_template('paperview_template.html', paper=paper,
                           search=search, comments=comments,
                           current=currentusers, paper_position=paper_position, searchquery = searchquery)


def create_papersearch_query(dbsession, searchid, initialquery=None, startdate=None,
                             enddate=None, refereed=None,
                             done=None, username=None, ident=None, currentuser=None):

    from sqlalchemy import distinct
    if not initialquery:
        query = dbsession.query(Paper).filter(Search.id==int(searchid))
    else:
        query=initialquery
    day = datetime.timedelta(days=1)

    if ident:
        # case insensitive search.
        ident = ident.lower()
        query = query.filter(Paper.identifiers.any(
            func.lower(Identifier.identifier).contains(ident.lower())))

    if startdate:
        start = datetime.datetime.strptime(startdate, '%Y-%m') - day
        query = query.filter(Paper.pubdate >= start)

    if enddate:
        end = datetime.datetime.strptime(enddate, '%Y-%m') + day
        query = query.filter(Paper.pubdate <= end)

    if refereed:
        if refereed.lower() == "true":
            refereed = True
        else:
            refereed = False
        query = query.filter(Paper.refereed == refereed)

    if currentuser is not None and username is None:
        username = currentuser

    if username:

        usernamequery = dbsession.query(Comment).filter(Comment.username==username).subquery()
        bcomm = aliased(Comment, usernamequery)
        usercommentcount = func.sum(bcomm.id.isnot(None)).label('usercommentcount')
        query = query.add_column(usercommentcount).outerjoin(bcomm, Paper.id==bcomm.paper_id)

    if done:

        if done.lower() == "true":
            done = True
        else:
            done = False

        if done is True:
            if Comment not in [mapper.class_ for mapper in query._join_entities] and \
                      Comment not in [i['entity'] for i in query.column_descriptions]:

                query = query.outerjoin(Comment, Paper.id==Comment.paper_id)
            if username:

                query = query.filter(Comment.username==username)
                # Find papers with comments by the named user.
                #subquery = dbsession.query(distinct(Comment.paper_id)).filter(Comment.username==username)
                #query = query.filter(Paper.id.in_(subquery))
        else:
            print('already classified is not True')
            if username:
                query = query.filter(usercommentcount == 0)
                # Search for papers with no comments from that user name.
                #subquery = dbsession.query(distinct(Comment.paper_id)).filter(Comment.username==username)
                #query = query.filter(Paper.id.notin_(subquery))
            else:
                # Search only for papers with no comments by anyone.
                print('finding papers with no comments')
                query = query.filter(Paper.comments == None)

    return query

#@auth.route('/search/<searchid>/commentsearch')
from sqlalchemy import func
def create_comment_search(dbsession, searchid, searchargs, paperargs=None):
    """Note: case insensitive matching.

    combine_or: if True, then multiple choice options will only demand
    one of the options in that sublist is met. Note that all of the
    sublists will still have to match.

    """
    print('creating commentsearch query')
    print(paperargs)

    commentcount = func.sum(Comment.id.isnot(None)).label('Commentcount')
    commentquery  = dbsession.query(Paper, Author.author, commentcount).outerjoin(Author, Paper.id==Author.paper_id).filter(Author.position_==0).outerjoin(Comment, Paper.id==Comment.paper_id).group_by(Paper.id)
    commentquery = commentquery.filter(Search.id==int(searchid))


    usernametype = searchargs.get('usernametype', 'perUser')
    combine_or = searchargs.get('combine_or', True)

    print('creating papertypes query')

    # First papertype.
    if 'papertype' in searchargs:
        papertypes = searchargs.getlist('papertype', int)
        if combine_or:
            commentquery = commentquery.filter(Comment.papertypevalues.any(
                PaperTypeValue.papertype_id.in_(papertypes)))
        else:
            for p in papertypes:
                commentquery = commentquery.filter(Comment.papertypevalues.any(papertype_id=p))

    # Now go through infosections

    # Now go through infosections
    infosections = [i for i in searchargs.keys() if i.startswith('infosection_')]
    infosectionqueries = []
    print('going through infosections')
    for isec in infosections:
        if searchargs[isec] and searchargs[isec] != '':
            isecid = int(isec.split('_')[1])
            infosection = dbsession.query(InfoSection).filter(InfoSection.id==isecid).one()
            if infosection.type_==isType.NOTES:
                # 1. Plain text fields: look for match within.
                notestext = searchargs[isec]

                commentquery = commentquery.filter(Comment.infosectionvalues.any(
                    func.lower(InfoSectionValue.entered_text).contains(notestext.lower()),
                    info_section_id=isecid))


            elif infosection.type_==isType.TEXTPERLINE:
                # 2. text per line: seperate each line,
                entries = searchargs[isec]
                entries = entries.split('\n')
                entries = [i.strip() for i in entries]
                for ent in entries:
                    commentquery = commentquery.filter(Comment.infosectionvalues.any(
                        func.lower(InfoSectionValue.entered_text).contains(ent.lower()),
                        info_section_id=isecid))
            else:
                # 3. sublists (radio or tick boxes irrelevant)
                sublistids = searchargs.getlist(isec, int)
                if combine_or:
                    commentquery = commentquery.filter(Comment.infosectionvalues.any(
                        InfosectionValue.info_sublist_id.in_(sublistids)))
                else:
                    for slid in sublistids:
                        commentquery = commentquery.filter(Comment.infosectionvalues.any(
                            info_sublist_id=slid, info_section_id=isecid))

    # Ensure you filter by paper values too.
    if paperargs:
        #commentquery = commentquery.join(Paper)
        commentquery = create_papersearch_query(dbsession, searchid, initialquery=commentquery, **paperargs)


    # Ensure you only get most recent, or most recent by user for
    if usernametype == 'overall':
        idlist = dbsession.query(func.max(Comment.id)).group_by(Comment.paper_id)
        commentquery = commentquery.filter(Comment.id.in_(idlist))
    elif usernametype == 'perUser':
        idlist = dbsession.query(func.max(Comment.id)).group_by(Comment.paper_id, Comment.username)
        commentquery = commentquery.filter(Comment.id.in_(idlist))

    return commentquery

@auth.route('/search/<searchid>/commentsearch')
def search_paper_list_bycomment(searchid):
    search = dbsession.query(Search).filter(Search.id==int(searchid)).one()

    searchargs = MultiDict()
    if request.args:
        searchargs.update(request.args)
        searchargs.update(MultiDict({'searchid': searchid}))
        commentfake = create_comment_from_request(searchargs, dbsession)
        startdate = request.args.get('startdate',None)
        enddate  = request.args.get('enddate', None)
        refereed = request.args.get('refereed', None)
        combine_or = bool(request.args.get('combine_or', True))

        username = request.args.get('username', None)
        ident = request.args.get('ident', None)
        querykwargs = dict(startdate=startdate,
                           enddate=enddate,
                           refereed=refereed,
                           done="true",
                           username=username,
                           ident=ident)
    else:
        commentfake=None
        querykwargs = dict(startdate=None,
                           enddate=None,
                           refereed=None,
                           done="true",
                           username=None,
                           ident=None)
    session['comment_query'] = searchargs.to_dict(flat=False)

    if 'searchid' in session['comment_query']:
        session['comment_query'].pop('searchid')

    query = create_comment_search(dbsession, search.id, searchargs, paperargs=querykwargs)

    papers = query.order_by(Comment.paper_id).all()

    return render_template('paperlist_commentsearch.html', commentfake=commentfake,
                           search=search, papers=papers, commentkwargs=searchargs,
                           querykwargs=querykwargs)

from ..summary_view import create_summary_by_papertype, create_summary_table_plots, create_summary_plots_mpl


@auth.route('/<searchid>/summarise_comments', methods=['GET', 'POST'])
def summarise_comments(searchid):
    dosearch = request.args.get('dosearch', 0, type=int)
    startdate = request.args.get('startdate',None)
    enddate  = request.args.get('enddate', None)
    refereed = request.args.get('refereed', None)
    username = request.args.get('username', None)
    ignored_papertype_ids = request.args.getlist('papertypes', type=int)
    ignored_infosection_ids = request.args.getlist('infosections', type=int)
    session = create_session()

    if refereed:
        if refereed.lower() == "true":
            refereed = True
        elif refereed.lower() == "false":
            refereed = False
        elif refereed.lower() == "either":
            refereed = None
        else:
            refereed = None
    querykwargs = {'startdate':startdate,
                   'enddate':enddate,
                   'refereed': refereed,
                   'username':username,
                   'ignored_papertype_ids': ignored_papertype_ids,
                   'ignored_infosection_ids': ignored_infosection_ids,
    }


    search = session.query(Search).filter(Search.id==searchid).one()
    if dosearch:
        if len(querykwargs['ignored_papertype_ids']) > 0:
            papertypes_to_query = search.papertypes
            papertypes_to_query = [p.id for p in papertypes_to_query
                                   if p.id not in querykwargs['ignored_papertype_ids']]
        else:
            papertypes_to_query = None

        print('paper types to query are', papertypes_to_query)

        if 'ignored_infosection_ids' in querykwargs:
            print('ignoring infosections {}'.format(querykwargs['ignored_infosection_ids']))
            infosections_to_query = search.infosections
            infosections_to_query = [p.id for p in infosections_to_query
                                   if p.id not in querykwargs['ignored_infosection_ids']]
            print('infosecitons_to_query are: {}'.format(infosections_to_query))
        else:
            print('no infosections being ignored')
            infosections_to_query = None

        missing_papers, res, overallsummary, overallsummarytable, ptypedict = create_summary_by_papertype(session,
                                                                             searchid,
                                                                             username=username,
                                                                             infosections_to_query=infosections_to_query,
                                                                             papertypes_to_query=papertypes_to_query,
                                                                             paperarguments=querykwargs)

        print('Creating plots!')
        mpldict = create_summary_plots_mpl(overallsummary, ptypedict)
        print('Created plots!')

    else:
        searchid = None
        overallsummary = None
        summarytables = None
        mpldict = None
        ptypedict = None
        missing_papers= None
        overallsummarytable = None


    return render_template('comment_summary.html', search=search, querykwargs=querykwargs, missing_papers=missing_papers,
                           searchid=searchid,
                           overallsummary=overallsummary, overallsummarytable=overallsummarytable,
                           mpldict=mpldict, ptypedict=ptypedict)



@auth.route('/search/<searchid>/paperlist')
def search_paper_list(searchid):
    print('Showing search_paper_list')
    search = dbsession.query(Search).filter(Search.id==int(searchid)).one()

    startdate = request.args.get('startdate',None)
    enddate  = request.args.get('enddate', None)
    refereed = request.args.get('refereed', None)
    done = request.args.get('done', None)
    username = request.args.get('username', None)
    ident = request.args.get('ident', None)

    querykwargs = dict(startdate=startdate,
                       enddate=enddate,
                       refereed=refereed,
                       done=done,
                       username=username,
                       ident=ident,
                       currentuser=getattr(current_user, 'username', None)
                       )

    print('query_kwargs are {}'.format(querykwargs))
    session['paper_query'] = querykwargs

    commentcount = func.sum(Comment.id.isnot(None)).label('Commentcount')

    query = dbsession.query(Paper, Author.author, commentcount).outerjoin(Author, Paper.id==Author.paper_id).filter(
        Author.position_==0).outerjoin(Comment, Paper.id==Comment.paper_id).group_by(Paper.id)

    query = query.filter(Search.id==int(searchid))

    query = create_papersearch_query(dbsession, search.id, initialquery=query, **querykwargs)

    print('query is {}'.format(query))
    papers = query.order_by(Paper.id).all()
    print('Found {} papers.'.format(len(papers)))
    # Filter within
    return render_template('paperlist.html', search=search, papers=papers, querykwargs=querykwargs)

@auth.route('/search/preview', methods=['POST'])
def preview_search():
    search = create_search_from_request(request)

    return render_template('displaysearch.html',search=search, preview=True)

@auth.route('/search/create', methods=['POST'])
def create_search():
    search = create_search_from_request(request)
    ses = dbsession
    ses.add(search)
    ses.commit()
    searchid = search.id
    raise werkzeug.routing.RequestRedirect(url_for('auth.search_info_page',
                                                   searchid=searchid, preview=False, create=True))

@auth.route('/search/<searchid>/paper/<paperid>/submit_comments', methods=['POST'])
def submit_paper(paperid, searchid):
    comment = create_comment_from_request(request.form, dbsession)
    dbsession.add(comment)
    dbsession.commit()

    flash('{} submitted comment for paper {}'.format(current_user.username, paperid))
    return redirect(url_for('auth.paper_info_page', paperid=paperid, searchid=searchid))



@auth.route('/search/<searchid>')
def search_info_page(searchid):
    preview = request.args.get('preview', False) == 'True'
    create = request.args.get('create', False) == 'True'
    ses = dbsession
    search = ses.query(Search).filter(Search.id==int(searchid)).one()
    return render_template('displaysearch.html', search=search, preview=preview, create=create)


@auth.route('/search/setup')
def search_setup_page():
    # Create Search
    return render_template('searchcreation.html')

@app.template_filter('datetime')
def datetime_filter(datetime):
    return datetime.strftime('%Y-%m-%d %H:%M')
@app.template_filter('pdflink')
def pdflink_filter(bibcode):
    pdflink = "http://adsabs.harvard.edu/cgi-bin/nph-data_query?bibcode={}&link_type=EJOURNAL"
    return pdflink.format(bibcode)

@app.template_filter('arxiv')
def arxiv_filter(paper):
    arxiv = [i.identifier for i in paper.identifiers
             if 'arXiv' in i.identifier]
    # Preferentially return the arXiv:XXXX format
    if arxiv:
        colonarxivs = [i for i in arxiv if ':' in i]
        if colonarxivs:
            return colonarxivs[0].split(':')[1]
        else:
            return arxiv[0]
    else:
        return None

@app.template_filter('classified_papers')
def classifed_papers(search):
    if search.comments:
        return set([i.paper_id for i in search.comments])
    else:
        return []

@app.template_filter('unique_affils')
def unique_affils(authorlist):
    """
    Return set of unique affilations from author list
    """
    affils = [a.affiliation for a in authorlist]
    uniqueaffils = set(affils)
    return uniqueaffils

@app.template_filter('unique_attr')
def unique_attr(listofobjs, attribute):
    """
    Return unique set of attribute values from list of objects.
    """
    attribs = [getattr(a, attribute) for a in listofobjs]
    return set(attribs)

@app.template_test('startswith')
def test_startswith(obj, startstring):
    if obj.startswith(startstring):
        return True
    else:
        return False
@app.template_filter('infosection_freeformtext')
def infosection_freeformtext(infosectiontype):
    """
    Return TRUE if it matches isType.NOTES, else False
    """
    if infosectiontype == isType.NOTES:
        return True
    else:
        return False
@app.template_filter('infosection_structtext')
def infosection_structtext(infosectiontype):
    """
    Return TRUE if it matches isType.TEXTPERLINE, else False
    """
    if infosectiontype == isType.TEXTPERLINE:
        return True
    else:
        return False

@app.template_filter('list')
def make_list(variable):
    return list(variable)

@app.template_filter('boolean_table')
def boolean_table(cellvalue, false=''):
    if isinstance(cellvalue, bool) or isinstance(cellvalue, np.bool_):
        if bool(cellvalue) is True:
            return '✓'
        elif bool(cellvalue) is False:
            return false
    else:
        return cellvalue


from urllib.parse import urlparse, urljoin
from flask import request, url_for

def is_safe_url(target):
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and \
           ref_url.netloc == test_url.netloc

@app.template_filter('debug')
def debug(text):
  print(text)
  return ''

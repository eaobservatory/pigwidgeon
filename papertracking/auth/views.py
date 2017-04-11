
from __future__ import absolute_import, division, print_function

from docopt import docopt
import functools
import os
from flask import Flask, redirect, url_for, render_template, request
import flask

from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy import create_engine, Column, ForeignKey, Unicode, UnicodeText, \
    Integer, String, Table, Unicode, Boolean, DateTime, func
from sqlalchemy.ext.declarative import declarative_base

import werkzeug.exceptions
import werkzeug.routing


from ..db import Paper, Search, PaperType, InfoSection, InfoSublist, Base, Comment
from ..search import create_search_from_request, create_comment_from_request
from ..paper import get_paper_info
from ..util import get_db_session, create_session, isType



from flask import request, render_template, render_template_string, flash, redirect, \
    url_for, Blueprint, g
from flask.ext.login import current_user, login_user, \
    logout_user, login_required
from papertracking import login_manager, ldap_manager
from papertracking.auth.user import User, LoginForm

from flask_ldap3_login.forms import LDAPLoginForm

from papertracking import app, users

auth = Blueprint('auth', __name__)



session = create_session()
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
    searches = session.query(Search).all()
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
    return redirect(url_for('auth.home'))

@auth.route('/search/<searchid>/paper/<paperid>')
def paper_info_page(paperid, searchid):
    session = create_session()
    search, paper = get_paper_info(paperid,searchid, session)
    comments = session.query(Comment).filter_by(search_id=searchid, paper_id=paperid).all()
    if hasattr(current_user, 'username'):
         currentusers_lastvalue = session.query(Comment).filter_by(search_id=searchid,
                                    paper_id=paperid,
                                    username=current_user.username
         ).order_by(Comment.datetime.desc()).first()
    else:
        currentusers_lastvalue = None

    return render_template('paperview_template.html', paper=paper,
                           search=search, comments=comments,
                           current=currentusers_lastvalue)

@auth.route('/search/<searchid>/paperlist')
def search_paper_list(searchid):
    search = session.query(Search).filter(Search.id==int(searchid)).one()
    return render_template('paperlist.html', search=search)

@auth.route('/search/preview', methods=['POST'])
def preview_search():
    search = create_search_from_request(request)

    return render_template('displaysearch.html',search=search, preview=True)

@auth.route('/search/create', methods=['POST'])
def create_search():
    search = create_search_from_request(request)
    ses = session
    ses.add(search)
    ses.commit()
    searchid = search.id
    raise werkzeug.routing.RequestRedirect(url_for('auth.search_info_page',
                                                   searchid=searchid, preview=False, create=True))

@auth.route('/search/<searchid>/paper/<paperid>/submit_comments', methods=['POST'])
def submit_paper(paperid, searchid):
    comment = create_comment_from_request(request, session)

    raise werkzeug.exceptions.InternalServerError('paper comments submission not yet supported')

@auth.route('/search/<searchid>')
def search_info_page(searchid):
    preview = request.args.get('preview', False) == 'True'
    create = request.args.get('create', False) == 'True'
    ses = session
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
from urllib.parse import urlparse, urljoin
from flask import request, url_for

def is_safe_url(target):
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and \
           ref_url.netloc == test_url.netloc


from __future__ import absolute_import, division, print_function

from docopt import docopt
import functools
import os
from flask import Flask, redirect, url_for, render_template, request

from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy import create_engine, Column, ForeignKey, Unicode, UnicodeText, \
    Integer, String, Table, Unicode, Boolean, DateTime, func
from sqlalchemy.ext.declarative import declarative_base

import werkzeug.exceptions
import werkzeug.routing


from ..db import Paper, Search, PaperType, InfoSection, InfoSublist, Base
from ..search import create_search_from_request, create_comment_from_request
from ..paper import get_paper_info
from ..util import get_db_session, create_session



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
        return redirect('/')
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

    return render_template('paperview_template.html', paper=paper, search=search)

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
    raise werkzeug.routing.RequestRedirect(url_for('search_info_page',
                                                   searchid=searchid, preview=False, create=True))

@auth.route('/search/<searchid>/paper/<paperid>/submit_comments', methods=['POST'])
def submit_paper(paperid, searchid):
    ses = session
    comment = create_comment_from_request(request, ses)
    print(comment)
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
    return set([i.paper_id for i in search.papertypevalues])

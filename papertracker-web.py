"""
Usage: papertracker-web.py [-h]
       papertracker-web.py [-d] [--port=port]

Launch a web page for testing

Options:
  -h --help  Show this help.
  -d --debug    Run using flasks debug mode. Allows reloading of code.
  -p --port=port  Port to run on (defaul tis 5000)


"""

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

from db import Paper, Search, PaperType, InfoSection, InfoSublist, Base
from search import create_search_from_request, create_comment_from_request
from paper import get_paper_info
from util import get_db_session, create_session



# Parse arguments
arguments = docopt(__doc__, help=True)
if arguments['--debug'] is True:
    host = '127.0.0.1'
    debug = True
else:
    host='0.0.0.0'
    debug = None

if arguments['--port']:
    port = int(arguments['--port'])
else:
    port = 5000


def papertracking_webapp():
    """
    Create web app for tracking paper relevancy.

    """
    app = Flask('Papermonitoring') 
    session = create_session()

    @app.route('/')
    def front_page():
        # Get all currently setup searches.
        searches = session.query(Search).all()

        return render_template('frontpage.html', searches=searches)

    @app.route('/search/<searchid>/paper/<paperid>')
    def paper_info_page(paperid, searchid):
        session = create_session()
        search, paper = get_paper_info(paperid,searchid, session)

        return render_template('paperview_template.html', paper=paper, search=search)

    @app.route('/search/preview', methods=['POST'])
    def preview_search():
        search = create_search_from_request(request)

        return render_template('displaysearch.html',search=search, preview=True)

    @app.route('/search/create', methods=['POST'])
    def create_search():
        search = create_search_from_request(request)
        ses = session
        ses.add(search)
        ses.commit()
        searchid = search.id
        raise werkzeug.routing.RequestRedirect(url_for('search_info_page',
                                                       searchid=searchid, preview=False, create=True))

    @app.route('/search/<searchid>/paper/<paperid>/submit_comments', methods=['POST'])
    def submit_paper(paperid, searchid):
        ses = session
        comment = create_comment_from_request(request, ses)
        raise werkzeug.exceptions.InternalServerError('paper comments submission not yet supported')

    @app.route('/search/<searchid>')
    def search_info_page(searchid):
        preview = request.args.get('preview', False) == 'True'
        create = request.args.get('create', False) == 'True'
        ses = session
        search = ses.query(Search).filter(Search.id==int(searchid)).one()
        return render_template('displaysearch.html', search=search, preview=preview, create=create)


    @app.route('/search/setup')
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

    return app



# Start flask app.
app = papertracking_webapp()
app.run(host=host, debug=debug, port=port)

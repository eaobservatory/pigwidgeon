"""
Usage: papertracker-web.py [-h]
       papertracker-web.py [-d]

Launch a web page for testing

Options:
  -h --help  Show this help.
  -d --debug    Run using flasks debug mode. Allows reloading of code.


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

from db import Paper, Search, PaperType, InfoSection, InfoSublist
from search import create_search_from_request
from util import get_db_session

# Parse arguments
arguments = docopt(__doc__, help=True)
if arguments['--debug'] is True:
    host = '127.0.0.1'
    debug = True
else:
    host='0.0.0.0'
    debug = None


def papertracking_webapp():
    """
    Create web app for tracking paper relevancy.

    """
    engine = create_engine('sqlite:///mydatabase.db')

    app = Flask('Papermonitoring')

    @app.route('/search/<searchid>/paper/<paperid>')
    def paper_info_page(paperid, searchid):
        return render_template('paperview_template.html', **get_paper_info(paperid, searchid))

    @app.route('/search/preview', methods=['POST'])
    def preview_search():
        search = create_search_from_request(request)

        return render_template('displaysearch.html',search=search, preview=True)

    @app.route('/search/create', methods=['POST'])
    def create_search():
        search = create_search_from_request(request)
        ses = get_db_session(engine)
        ses.add(search)
        ses.commit()
        return render_template('displaysearch.html',
                               search=search,
                               preview=False, create=True)

    @app.route('/search/<searchid>')
    def search_info_page(searchid):
        ses = get_db_session(engine)
        search = ses.query(Search).filter(Search.id==int(searchid)).one()
        return render_template('displaysearch.html', search=search)


    @app.route('/search/setup')
    def search_setup_page():
        # Create Search
        return render_template('searchcreation.html')

    def get_paper_info(paperid, searchid):
        """
        Get summary info of paper.

        Using testd b.
        """

        paperid = int(paperid)
        searchid = int(searchid)

        ses = get_db_session(engine)

        # Get search and paper
        search = ses.query(Search).filter(Search.id==searchid).one()
        print(search)
        paper = ses.query(Paper).filter(Paper.id==paperid).one()

        # Check if paper is in search: display warning if not?
        # More efficient way to do this?
        if search.id in [i.id for i in paper.searches]:
            paper_belongs = True
        else:
            paper_belongs = False

        results = paper.__dict__.copy()
        results['authors'] = paper.authors
        results['keywords'] = paper.keywords
        results['identifiers'] = paper.identifiers
        results['properties'] = paper.properties

        ses.commit()
        results['search_name'] = search.named

        # results = paperdict[paperid]
        # # Fix up various things
        # if not isinstance(results['doi'], str):
        #     results['doi'] = results['doi'][0]
        properties = set([i.property for i in results['properties']])
        props_we_want=set(['REFEREED','PUB_OPENACCESS', 'NOT REFEREED'])
        properties = props_we_want.intersection(properties)
        results['properties'] = properties

        if 'PUB_OPENACCESS' in results['properties']:
             results['pub_pdf_link'] = "http://adsabs.harvard.edu/cgi-bin/nph-data_query?bibcode={}&link_type=ARTICLE".format(results['bibcode'])

        identifiers = results['identifiers']
        arxiv_1 = [i.identifier for i in identifiers if i.identifier.startswith('arXiv:')]
        if arxiv_1:
            results['arxiv'] = arxiv_1[0].split(':')[1]
        else:
            arxiv_2 = [i.identifier for i in identifiers if 'arXiv' in i.identifier]
            if arxiv_2:
                results['arxiv'] = arxiv_2[0]


        # Search stuff.
        results['search_papertypes'] = search.papertypes
        print(search.papertypes)
        results['search_infosections'] = search.infosections
        results['search_sublists'] = {}
        for i in search.infosections:
            results['search_sublists'][i.name_code] = i.sublists
        return results

    @app.template_filter('pdflink')
    def pdflink_filter(bibcode):
        pdflink = "http://adsabs.harvard.edu/cgi-bin/nph-data_query?bibcode={}&link_type=ARTICLE"
        return pdflink.format(bibcode)
    return app



# Start flask app.
app = papertracking_webapp()
app.run(host=host, debug=debug)

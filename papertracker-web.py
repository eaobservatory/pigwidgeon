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

    @app.route('/preview_search', methods=['POST'])
    def preview_search():
        search = create_search_from_request(request)
        print('In preview search!')
        return render_template('displaysearch.html',search=search, preview=True)

    @app.route('/create_search', methods=['POST'])
    def create_search():
        search = create_search_from_request(request)
        ses = create_db(engine)
        ses.add(search)
        print([i.name_ for i in search.infosections])
        ses.commit()
        
        return render_template('displaysearch.html', search=search, preview=False, create=True)
    @app.route('/search/<searchid>')
    def search_info_page(searchid):
        ses = create_db(engine)
        search = ses.query(Search).filter(Search.id==int(searchid)).one()
        return render_template('displaysearch.html', search=search)
    
    def create_search_from_request(request):
        """
        Create a db.Search object from data in a request FORM header.

        Assumes the POST to the FORM set everything up sensibly.
        """
        searchname = request.form.get('searchname', None)
        if not searchname:
            raise werkzeug.exceptions.InternalServerError('No searchname set. Please use the browser\'s back button to return to your search query setup.')
        adsquery = request.form.get('adsquery', None)
        if not adsquery:
            raise werkzeug.exceptions.InternalServerError('No ads query set. Please use the browser\'s back button to return to your search query setup.')
        ptnames = request.form.getlist('ptname')
        ptradios = [request.form.get('ptradio' + str(i+1), False)=='on' for i in range(len(ptnames))]
        infonames = request.form.getlist('infoname')
        infotexts = request.form.getlist('infotext')
        infotypes = [int(i) for i in request.form.getlist('infotype')]
        infosublistids = request.form.getlist('infosublistid')
        infosublistentries = request.form.getlist('infosublistentry')
        # Create a Search object
        ptname_codes = [str(i) for i in range(len(ptnames))]
        papertypes = [PaperType(name_=i, name_code=j, radio=k)
                      for i, j,k in zip(ptnames, ptname_codes, ptradios)]
        is_codes = [str(i) for i in range(len(infonames))]
        print(len(infonames), len(is_codes), len(infotypes), len(infotexts))
        infosections = [InfoSection(name_=i, name_code=j, type_=k,
                                    position_=infonames.index(i), instructiontext=l)
                        for i,j,k,l in zip(infonames, is_codes, infotypes, infotexts)]
        print(', '.join([str(i.name_)+str(i.position_) for i in infosections]))
        if infosublistids and infosublistentries:
            for i in set(infosublistids):
               sublistentries = [
                   infosublistentries[j] for j in range(len(infosublistids))
                   if infosublistids[j] == i]
               sublists = [InfoSublist(named=j,
                                       position_=sublistentries.index(j))
                           for j in sublistentries]
               infosections[int(i)-1].sublists=sublists
        # Validate one thing:
        for  i in infosections:
            if i.type_ not in [0,1]:
                if i.sublists and len(i.sublists)!=0:
                    print(i.name_, i.type_, i.sublists)
                    raise werkzeug.exceptions.InternalServerError('This search has sublists for a a text entry type. If you are creating a search, please use the back button to fix this.')
        search = Search(named=searchname, ads_query=adsquery, last_performed=None,
               startdate=None,
               papertypes=papertypes, infosections=infosections)
        return search

    @app.route('/search/setup')
    def search_setup_page():
        # Create Search
        return render_template('searchcreation.html')

    def create_db(engine):
        # Set up DB stuff.

        Base = declarative_base()
        Session = sessionmaker(bind=engine)
        ses = Session()
        return ses

    def get_paper_info(paperid, searchid):
        """
        Get summary info of paper.

        Using testd b.
        """

        paperid = int(paperid)
        searchid = int(searchid)

        create_db(engine)
        # Get search and paper
        search = ses.query(Search).filter(Search.id==searchid).one()
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

    return app



paper1 ={'abstract': 'SCUBA-2 is a 10 000-bolometer submillimetre camera on the James Clerk Maxwell Telescope. The instrument commissioning was completed in 2011 September, and full science operations began in 2011 October. To harness the full potential of this powerful new astronomical tool, the instrument calibration must be accurate and well understood. To this end, the algorithms for calculating the line-of-sight opacity have been improved, and the derived atmospheric extinction relationships at both wavebands of the SCUBA-2 instrument are presented. The results from over 500 primary and secondary calibrator observations have allowed accurate determination of the flux conversion factors (FCF) for the 850 and 450 μm arrays. Descriptions of the instrument beam shape and photometry methods are presented. The calibration factors are well determined, with relative calibration accuracy better than 5 per cent at 850 μm and 10 per cent at 450 μm, reflecting the success of the derived opacity relations as well as the stability of the performance of the instrument over several months. The sample size of the calibration observations and accurate FCFs have allowed the determination of the 850 and 450 μm fluxes of several well-known submillimetre sources, and these results are compared with previous measurements from SCUBA.',
 'author': ['Dempsey, J. T.',
  'Friberg, P.',
  'Jenness, T.',
  'Tilanus, R. P. J.',
  'Thomas, H. S.',
  'Holland, W. S.',
  'Bintley, D.',
  'Berry, D. S.',
  'Chapin, E. L.',
  'Chrysostomou, A.',
  'Davis, G. R.',
  'Gibb, A. G.',
  'Parsons, H.',
  'Robson, E. I.'],
 'bibcode': '2013MNRAS.430.2534D',
 'doi': ['10.1093/mnras/stt090'],
 'first_author': 'Dempsey, J. T.',
 'id': '2026500',
 'keyword': ['atmospheric effects',
  'submillimetre: general',
  'Astrophysics - Instrumentation and Methods for Astrophysics'],
 'property': ['OPENACCESS',
  'REFEREED',
  'EPRINT_OPENACCESS',
  'PUB_OPENACCESS',
  'ARTICLE'],
 'title': ['SCUBA-2: on-sky calibration using submillimetre standard sources'],
 'year': '2013',
  'identifier': ['2013arXiv1301.3773D',
  '2013MNRAS.430.2534D',
  '2013arXiv1301.3773D',
  '10.1093/mnras/stt090',
  'arXiv:1301.3773',
  '10.1093/mnras/stt090'],}



paperdict={'0': {'abstract': 'Commissioning of SCUBA-2 included a program of skydips and observations of calibration sources intended to be folded into regular observing as standard methods of source flux calibration and to monitor the atmospheric opacity and stability. During commissioning, it was found that these methods could also be utilised to characterise the fundamental instrument response to sky noise and astronomical signals. Novel techniques for analysing onsky performance and atmospheric conditions are presented, along with results from the calibration observations and skydips.',
  'author': ['Dempsey, Jessica T.',
   'Friberg, Per',
   'Jenness, Tim',
   'Bintley, Dan',
   'Holland, Wayne S.'],
  'bibcode': '2010SPIE.7741E..1XD',
  'doi': ['10.1117/12.856476'],
  'first_author': 'Dempsey, Jessica T.',
  'id': '1864369',
  'identifier': ['2010arXiv1008.0890D',
   '2010SPIE.7741E..54D',
   '2010SPIE.7741E..1XD',
   '10.1117/12.856476',
   '2010arXiv1008.0890D',
   'arXiv:1008.0890',
   '2010SPIE.7741E..54D',
   '10.1117/12.856476'],
  'keyword': ['Astrophysics - Instrumentation and Methods for Astrophysics'],
  'property': ['OPENACCESS', 'EPRINT_OPENACCESS', 'ARTICLE', 'NOT REFEREED'],
  'title': ['Extinction correction and on-sky calibration of SCUBA-2'],
  'year': '2010'},
 '1': {'abstract': 'SCUBA-2 is a 10 000-bolometer submillimetre camera on the James Clerk Maxwell Telescope. The instrument commissioning was completed in 2011 September, and full science operations began in 2011 October. To harness the full potential of this powerful new astronomical tool, the instrument calibration must be accurate and well understood. To this end, the algorithms for calculating the line-of-sight opacity have been improved, and the derived atmospheric extinction relationships at both wavebands of the SCUBA-2 instrument are presented. The results from over 500 primary and secondary calibrator observations have allowed accurate determination of the flux conversion factors (FCF) for the 850 and 450 μm arrays. Descriptions of the instrument beam shape and photometry methods are presented. The calibration factors are well determined, with relative calibration accuracy better than 5 per cent at 850 μm and 10 per cent at 450 μm, reflecting the success of the derived opacity relations as well as the stability of the performance of the instrument over several months. The sample size of the calibration observations and accurate FCFs have allowed the determination of the 850 and 450 μm fluxes of several well-known submillimetre sources, and these results are compared with previous measurements from SCUBA.',
  'author': ['Dempsey, J. T.',
   'Friberg, P.',
   'Jenness, T.',
   'Tilanus, R. P. J.',
   'Thomas, H. S.',
   'Holland, W. S.',
   'Bintley, D.',
   'Berry, D. S.',
   'Chapin, E. L.',
   'Chrysostomou, A.',
   'Davis, G. R.',
   'Gibb, A. G.',
   'Parsons, H.',
   'Robson, E. I.'],
  'bibcode': '2013MNRAS.430.2534D',
  'doi': ['10.1093/mnras/stt090'],
  'first_author': 'Dempsey, J. T.',
  'id': '2026500',
  'identifier': ['2013arXiv1301.3773D',
   '2013MNRAS.430.2534D',
   '2013arXiv1301.3773D',
   '10.1093/mnras/stt090',
   'arXiv:1301.3773',
   '10.1093/mnras/stt090'],
  'keyword': ['atmospheric effects',
   'submillimetre: general',
   'Astrophysics - Instrumentation and Methods for Astrophysics'],
  'property': ['OPENACCESS',
   'REFEREED',
   'EPRINT_OPENACCESS',
   'PUB_OPENACCESS',
   'ARTICLE'],
  'title': ['SCUBA-2: on-sky calibration using submillimetre standard sources'],
  'year': '2013'},
 '2': {'abstract': 'SCUBA-2 is the largest submillimetre wide-field bolometric camera ever built. This 43 square arc- minute field-of-view instrument operates at two wavelengths (850 and 450 microns) and has been installed on the James Clerk Maxwell Telescope on Mauna Kea, Hawaii. SCUBA-2 has been successfully commissioned and operational for general science since October 2011. This paper presents an overview of the on-sky performance of the instrument during and since commissioning in mid- 2011. The on-sky noise characteristics and NEPs of the 450 μm and 850 μm arrays, with average yields of approximately 3400 bolometers at each wavelength, will be shown. The observing modes of the instrument and the on-sky calibration techniques are described. The culmination of these efforts has resulted in a scientifically powerful mapping camera with sensitivities that allow a square degree of sky to be mapped to 10 mJy/beam rms at 850 μm in 2 hours and 60 mJy/beam rms at 450 μm in 5 hours in the best weather.',
  'author': ['Dempsey, Jessica T.',
   'Holland, Wayne S.',
   'Chrysostomou, Antonio',
   'Berry, David S.',
   'Bintley, Daniel',
   'Chapin, Edward L.',
   'Craig, Simon C.',
   'Coulson, Iain M.',
   'Davis, Gary R.',
   'Friberg, Per',
   'Jenness, Tim',
   'Gibb, Andy G.',
   'Parsons, Harriet A. L.',
   'Scott, Douglas',
   'Thomas, Holly S.',
   'Tilanus, Remo P. J.',
   'Robson, Ian',
   'Walther, Craig A.'],
  'bibcode': '2012SPIE.8452E..02D',
  'doi': ['10.1117/12.926547'],
  'first_author': 'Dempsey, Jessica T.',
  'id': '1987069',
  'identifier': ['2012arXiv1208.4622D',
   '2012SPIE.8452E..02D',
   'arXiv:1208.4622',
   '2012arXiv1208.4622D',
   '10.1117/12.926547',
   '10.1117/12.926547'],
  'keyword': ['Astrophysics - Instrumentation and Methods for Astrophysics'],
  'property': ['OPENACCESS', 'EPRINT_OPENACCESS', 'ARTICLE', 'NOT REFEREED'],
  'title': ['A new era of wide-field submillimetre imaging: on-sky performance of SCUBA-2'],
  'year': '2012'},
 '3': {'abstract': 'A 183GHz water vapour radiometer is installed at the JCMT, but is not currently used for active atmospheric calibration. With the installation of the SCUBA-2 submillimetre camera, it is desirable to provide more accurate and time-sensitive calibration at specific wavelengths. It is shown here that the 183GHz water vapour monitor data can be used to calculate the atmospheric opacity over small time-scales, directly along the line-of-sight of the instrument. These data will be used to identify the potential for improvement in existing calibration schemes, and the requirements of such a system if used with an instrument such as SCUBA-2.',
  'author': ['Dempsey, Jessica T.', 'Friberg, Per'],
  'bibcode': '2008SPIE.7012E..3ZD',
  'doi': ['10.1117/12.787471'],
  'first_author': 'Dempsey, Jessica T.',
  'id': '1737644',
  'identifier': ['2008SPIE.7012E.137D',
   '2008SPIE.7012E.137D',
   '10.1117/12.787471',
   '10.1117/12.787471',
   '2008SPIE.7012E..3ZD'],
  'keyword': None,
  'property': ['ARTICLE', 'NOT REFEREED'],
  'title': ['Optimizing atmospheric correction at the JCMT using a 183GHz water vapor radiometer'],
  'year': '2008'},
 '4': {'abstract': 'We present the first release (R1) of data from the CO High-Resolution Survey (COHRS), which maps a strip of the inner Galactic plane in <SUP>12</SUP>CO (J = 3 → 2). The data are taken using the Heterodyne Array Receiver Programme on the James Clerk Maxwell Telescope (JCMT) in Hawaii, which has a 14 arcsec angular resolution at this frequency. When complete, this survey will cover |b| 〈= 0.°5 between 10° 〈 l 〈 65°. This first release covers |b| 〈= 0.°5 between 10.°25 〈 l 〈 17.°5 and 50.°25 〈 l 〈 55.°25, and |b| 〈= 0.°25 between 17.°5 〈 l 〈 50.°25. The data are smoothed to a velocity resolution of 1 km s<SUP>-1</SUP>, a spatial resolution of 16 arcsec and achieve a mean rms of ~1 K. COHRS data are available to the community online at <A href="http://dx.doi.org/10.11570/13.0002">http://dx.doi.org/10.11570/13.0002</A>. In this paper we describe the data acquisition and reduction techniques used and present integrated intensity images and longitude-velocity maps. We also discuss the noise characteristics of the data. The high resolution is a powerful tool for morphological studies of bubbles and filaments while the velocity information shows the spiral arms and outflows. These data are intended to complement both existing and upcoming surveys, e.g., the Bolocam Galactic Plane Survey (BGPS), ATLASGAL, the Herschel Galactic Plane Survey (Hi-GAL) and the JCMT Galactic Plane Survey with SCUBA-2 (JPS).',
  'author': ['Dempsey, J. T.', 'Thomas, H. S.', 'Currie, M. J.'],
  'bibcode': '2013ApJS..209....8D',
  'doi': ['10.1088/0067-0049/209/1/8'],
  'first_author': 'Dempsey, J. T.',
  'id': '2001923',
  'identifier': ['2013ApJS..209....8D',
   '10.1088/0067-0049/209/1/8',
   '10.1088/0067-0049/209/1/8'],
  'keyword': ['ISM: clouds',
   'ISM: structure',
   'molecular data',
   'stars: massive',
   'submillimeter: ISM',
   'surveys'],
  'property': ['OPENACCESS', 'REFEREED', 'PUB_OPENACCESS', 'ARTICLE'],
  'title': ['CO (3 - 2) High-resolution Survey of the Galactic Plane: R1'],
  'year': '2013'},
 '5': {'abstract': 'The James Clerk Maxwell Telescope (JCMT) is the largest single-dish submillimetre telescope in the world, and throughout its lifetime the volume and impact of its science output have steadily increased. A key factor for this continuing productivity is an ever-evolving approach to optimising operations, data acquisition, and science product pipelines and archives. The JCMT was one of the first common-user telescopes to adopt flexible scheduling in 2003, and its impact over a decade of observing will be presented. The introduction of an advanced data-reduction pipeline played an integral role, both for fast real-time reduction during observing, and for science-grade reduction in support of individual projects, legacy surveys, and the JCMT Science Archive. More recently, these foundations have facilitated the commencement of remote observing in addition to traditional on-site operations to further increase on-sky science time. The contribution of highly-trained and engaged operators, support and technical staff to efficient operations will be described. The long-term returns of this evolution are presented here, noting they were achieved in face of external pressures for leaner operating budgets and reduced staffing levels. In an era when visiting observers are being phased out of many observatories, we argue that maintaining a critical level of observer participation is vital to improving and maintaining scientific productivity and facility longevity.',
  'author': ['Dempsey, Jessica T.',
   'Bell, Graham S.',
   'Chrysostomou, Antonio',
   'Coulson, Iain M.',
   'Davis, Gary R.',
   'Economou, Frossie',
   'Friberg, Per',
   'Jenness, Timothy',
   'Johnstone, Doug',
   'Tilanus, Remo P. J.',
   'Thomas, Holly S.',
   'Walther, Craig A.'],
  'bibcode': '2014SPIE.9149E..1FD',
  'doi': ['10.1117/12.2056862'],
  'first_author': 'Dempsey, Jessica T.',
  'id': '2082387',
  'identifier': ['10.1117/12.2056862',
   '10.1117/12.2056862',
   '2014SPIE.9149E..1FD'],
  'keyword': None,
  'property': ['ARTICLE', 'NOT REFEREED'],
  'title': ['Setting the standard: 25 years of operating the JCMT'],
  'year': '2014'}}



# Start flask app.
app = papertracking_webapp()
app.run(host=host, debug=debug)

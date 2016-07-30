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

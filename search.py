"""
Functions related to search creation and viewing
"""

import werkzeug.exceptions

from db import Search, PaperType, InfoSection, InfoSublist
from util import isType
def create_search_from_request(request):
    """Create a db.Search object from data in a request FORM header.

    Assumes the POST to the FORM set everything up sensibly.

    While it doesn't do full checking, it will raise an internal
    server error if the searchname is not set, if the ads_query is not
    set, or if there are sublist entries for info sections

    """
    searchname = request.form.get('searchname', None)
    if not searchname:
        raise werkzeug.exceptions.InternalServerError('No searchname set. Please use the browser\'s back button to return to your search query setup.')

    adsquery = request.form.get('adsquery', None)
    if not adsquery:
        raise werkzeug.exceptions.InternalServerError('No ads query set. Please use the browser\'s back button to return to your search query setup.')

    # Paper type information.
    ptnames = request.form.getlist('ptname')
    ptradios = [request.form.get('ptradio' + str(i+1), False)=='on'
                for i in range(len(ptnames))]
    ptname_codes = [str(i) for i in range(len(ptnames))]
    papertypes = [PaperType(name_=i, name_code=j, radio=k)
                  for i, j,k in zip(ptnames, ptname_codes, ptradios)]

    # Infosection information.
    infonames = request.form.getlist('infoname')
    infotexts = request.form.getlist('infotext')
    infotypes = [int(i) for i in request.form.getlist('infotype')]
    is_codes = [str(i) for i in range(len(infonames))]
    infosections = [InfoSection(name_=i, name_code=j, type_=k,
                                position_=infonames.index(i), instructiontext=l)
                    for i,j,k,l in zip(infonames, is_codes, infotypes, infotexts)]

    # Infosection sublist information.
    infosublistids = request.form.getlist('infosublistid')
    infosublistentries = request.form.getlist('infosublistentry')

    # Connect infosection and infosublists
    if infosublistids and infosublistentries:
        for i in set(infosublistids):
           sublistentries = [
               infosublistentries[j] for j in range(len(infosublistids))
               if infosublistids[j] == i]
           sublists = [InfoSublist(named=j, position_=sublistentries.index(j))
                       for j in sublistentries]
           infosections[int(i)-1].sublists=sublists

    # Validate one thing:
    for  i in infosections:
        if i.type_ not in [isType.RADIO,isType.CHECK]:
            if i.sublists and len(i.sublists)!=0:
                raise werkzeug.exceptions.InternalServerError('This search has sublists for a a text entry type. If you are creating a search, please use the back button to fix this.')

    # Create search object
    search = Search(named=searchname, ads_query=adsquery, last_performed=None,
           startdate=None, papertypes=papertypes, infosections=infosections)

    return search

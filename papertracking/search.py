"""
Functions related to search creation and viewing
"""

import werkzeug.exceptions

from .db import Search, PaperType, InfoSection, InfoSublist, PaperTypeValue, InfoSectionValue, Comment
from .util import isType
import datetime

def create_comment_from_request(request, ses):
    """
    Create a comment for a paper from a POST request object.

    """
    print(request.form)
    searchid = int(request.form.get('searchid', None))
    paperid = int(request.form.get('paperid', None))
    username = request.form.get('username')

    comment = Comment(search_id=searchid, paper_id=paperid, username=username)
    search = ses.query(Search).filter(Search.id==int(searchid)).one()
    infosections = search.infosections

    #for i in infosections:
    #    if i.sublists:
    #        for s in i.sublists:
    #            print(s.named, s.position_, s.entry_value)

    # First: papertypes
    papertype_ids = request.form.getlist('papertype')
    papertypevalues = [PaperTypeValue(papertype_id=int(i), comment=comment)
                       for i in papertype_ids]

    # Second: all remaining infosection comments
    # 0. List to hold results:
    isvalues = []

    # 1. get the keys form the comment dictionary.
    infosections = [i for i in request.form.keys() if i.startswith('infosection_')]

    # For each one, get the infosecitonid, the sublistid, and the value
    infosectionid = [int(i.split('_')[1]) for i in infosections]

    # Now go through each InfoSection key, and create an InfoSectionValue object.
    for isid in infosectionid:
        isection = [s for s in search.infosections if int(s.id)==isid][0]
        values = request.form.getlist('infosection_'+str(isid))

        if isection.type_  in [isType.RADIO, isType.CHECK]:
            for value in values:
                isvalues.append(InfoSectionValue(info_section_id=isid,
                                                 info_sublist_id=int(value),
                                             comment=comment))
        elif isection.type_ == isType.TEXTPERLINE:
            if len(values) > 1:
                logger.warning('Multiple values found for TEXTPERLINE TYPE. Only first being used.')

            # break up into separate sections and write down.
            entered_text = values[0]
            values = entered_text.split()
            isvalues+=[
                InfoSectionValue(info_section_id=isid,
                                 entered_text=v, comment=comment) for v in values]
        else:
            if len(values) > 1:
                logger.warning('Multiple values found for NOTES TYPE. Only first being used.')
            entered_text = values[0]
            isvalues.append(InfoSectionValue(info_section_id=isection.id,
                                             entered_text=entered_text,
                                             comment=comment))

    ses.add(comment)
    for i in isvalues:
        ses.add(i)
    for i in papertypevalues:
        ses.add(i)

    ses.commit()


def create_search_from_request(request):
    """Create a db.Search object from data in a request FORM header.

    Assumes the POST to the FORM set everything up sensibly.

    While it doesn't do full checking, it will raise an internal
    server error if the searchname is not set, if the ads_query is not
    set, or if there are sublist entries for info sections that don't
    support them.

    """
    searchname = request.form.get('searchname', None)
    if not searchname:
        raise werkzeug.exceptions.InternalServerError('No searchname set. Please use the browser\'s back button to return to your search query setup.')

    adsquery = request.form.get('adsquery', None)
    if not adsquery:
        raise werkzeug.exceptions.InternalServerError('No ads query set. Please use the browser\'s back button to return to your search query setup.')
    startdate = request.form.get('startdate', None)
#    try:
    year = int(startdate[0:4])
    month = int(startdate[4:6])
    day = 1
    startdate = datetime.date(year, month, day)
#    except:
#        raise werkzeug.exceptions.InternalServerError('Start date not set or could not be converted to datetime.date. Please user the browser\'s back button to return to your search query setup.')
    timerange = int(request.form.get('timerange', 3))

    # Paper type information.
    ptnames = request.form.getlist('ptname')
    ptradios = [request.form.get('ptradio' + str(i+1), False)=='on'
                for i in range(len(ptnames))]
    papertypes = [PaperType(name_=i, radio=j)
                  for i, j in zip(ptnames, ptradios)]

    # Infosection information.
    infonames = request.form.getlist('infoname')
    infotexts = request.form.getlist('infotext')
    infotypes = [int(i) for i in request.form.getlist('infotype')]
    infosections = [InfoSection(name_=i, type_=j,
                                position_=infonames.index(i), instructiontext=k)
                    for i,j,k in zip(infonames, infotypes, infotexts)]

    # Infosection sublist information.
    infosublistids = request.form.getlist('infosublistid')
    if infosublistids == ['']:
        infosublistids = None
    infosublistentries = request.form.getlist('infosublistentry')
    if infosublistentries == ['']:
        infosublistentries = None

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
    search = Search(named=searchname, startdate=startdate,
                    timerange=timerange,ads_query=adsquery,
                    last_performed=None, papertypes=papertypes,
                    infosections=infosections)

    return search

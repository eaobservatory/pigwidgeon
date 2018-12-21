#!/usr/bin/env python


"""
Usage: papertracking-update.py [-v] <searchid> [--dryrun] [--start=<start>] [--end=<end>]

PaperTracking: Update the ADS search with the given ID.

Options:
  -h --help          Show this help.
  -v --verbose       DEBUG logging level
  -d --dryrun        Run query but don't update DB
  -s --start=<start> Start date for query (YYYY-MM)
  -e --end=<end>     End date for query (YYYY-MM)
"""

from docopt import docopt

from papertracking.util import create_session
from papertracking import query
import logging
import datetime

arguments = docopt(__doc__, help=True)

if arguments['--verbose'] is True:
    logging.basicConfig(level=logging.DEBUG)
else:
    logging.basicConfig(level=logging.INFO)

searchid = arguments['<searchid>']
dryrun = arguments['--dryrun']
end = arguments['--end']
start = arguments['--start']
if start:
    start = datetime.datetime.strptime(start, '%Y-%m')
if end:
    end = datetime.datetime.strptime(end, '%Y-%m')

session = create_session()
query.update_search(1, session, dryrun=dryrun, startdate=start, enddate=end)

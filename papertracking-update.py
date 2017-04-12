#!/usr/bin/env python


"""
Usage: papertracking-update.py [-v] <searchid> [--dryrun]

PaperTracking: Update the ADS search with the given ID.

Options:
  -h --help       Show this help.
  -v --verbose    DEBUG logging level
  -d --dryrun     Run query but don't update DB
"""

from docopt import docopt

from papertracking.util import create_session
from papertracking import query
import logging

arguments = docopt(__doc__, help=True)

if arguments['--verbose'] is True:
    logging.basicConfig(level=logging.DEBUG)
else:
    logging.basicConfig(level=logging.INFO)

searchid = arguments['<searchid>']
dryrun = arguments['--dryrun']


session = create_session()
query.update_search(1, session, dryrun=dryrun)

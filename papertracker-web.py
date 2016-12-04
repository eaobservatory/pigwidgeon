"""
Usage: papertracker-web.py [-h]
       papertracker-web.py [-d] [--port=port]

Launch a web page for testing

Options:
  -h --help  Show this help.
  -d --debug    Run using flasks debug mode. Allows reloading of code.
  -p --port=port  Port to run on (defaul tis 5000)


"""



from docopt import docopt
from papertracking import app

# Start flask app.
# Parse arguments
arguments = docopt(__doc__, help=True)
if arguments['--debug'] is True:
    host = '127.0.0.1'
    debug = True
    app.jinja_env.auto_reload=True
else:
    host='0.0.0.0'
    debug = None

if arguments['--port']:
    port = int(arguments['--port'])
else:
    port = 5000


app.run(host=host, debug=debug, port=port)

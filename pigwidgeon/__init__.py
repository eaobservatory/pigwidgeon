from flask import Flask, redirect
from flask_login import LoginManager
from flask_ldap3_login import LDAP3LoginManager

import dash

import logging
logging.basicConfig(level=logging.DEBUG)

app = Flask('Pigwidgeon')

# LDAP Configuration Variables

# Hostname of your LDAP Server
app.config['LDAP_HOST'] = '10.100.1.1'

# Base DN of your directory
app.config['LDAP_BASE_DN'] = 'dc=eao,dc=hawaii,dc=edu'

# Users DN to be prepended to the Base DN
app.config['LDAP_USER_DN'] = 'ou=People'

# Groups DN to be prepended to the Base DN
app.config['LDAP_GROUP_DN'] = 'ou=Groups'

# The RDN attribute for your user schema on LDAP
app.config['LDAP_USER_RDN_ATTR'] = 'cn'

# The Attribute you want users to authenticate to LDAP with.
# Use 'mail' to use email logins instead.
app.config['LDAP_USER_LOGIN_ATTR'] = 'uid'

# The Username to bind to LDAP with
app.config['LDAP_BIND_USER_DN'] = None

# The Password to bind to LDAP with
app.config['LDAP_BIND_USER_PASSWORD'] = None


app.config['LDAP_GROUP_MEMBERS_ATTR'] = 'memberUid'
app.config['LDAP_GROUP_OBJECT_FILTER'] =  '(objectclass=posixGroup)'

app.secret_key = 'random key'

app.secret_key = 'random key'

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'
ldap_manager = LDAP3LoginManager(app)
users = {}

from .auth.views import auth
app.register_blueprint(auth)


from .views.jcmt import jcmt
app.register_blueprint(jcmt)



app_dash = dash.Dash('Pigwidgeon', server=app, url_base_pathname='/jcmt-dash-basic/',
                     external_stylesheets= ['https://codepen.io/chriddyp/pen/bWLwgP.css'])

app_dash.config['suppress_callback_exceptions']=True


from .dash_app import create_dash_app
create_dash_app(app_dash)



@app.route('/jcmt-dashboard')
def jcmt_dashboard():
    return redirect('/jcmt-dash-basic/')

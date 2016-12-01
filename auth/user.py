import ldap
from flask_wtf import Form
from wtforms import TextField, PasswordField
from wtforms.validators import InputRequired
from flask_login import UserMixin

from papertracking import users

def get_ldap_connection():
    conn = ldap.initialize(app.config['LDAP_PROVIDER_URL'])
    return conn

class User(UserMixin):

    def __init__(self, dn, username, data):
        self.dn = dn
        self.username = username
        self.data = data

    @staticmethod
    def try_login(username, password):
        conn = get_ldap_connection()
        conn.simple_bind(
            'cn={},ou=People,dc=eao,dc=hawaii,dc=edu'.format(username),
            password)

    #def is_authenticated(self):
    #     return True

    # def is_active(self):
    #     return True

    # def is_anonymous(self):
    #     return False


    def get_id(self):
        return self.dn


class LoginForm(Form):
    username = TextField('Username', [InputRequired()])
    password = PasswordField('Password', [InputRequired()])

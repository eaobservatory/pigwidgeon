import configparser
import os

config = None
home_directory = None

config_file = ('etc', 'pigwidgeon.ini')

def get_config():
    """
    Read the configuration file.

    Return a ConfigParser object.

    Raise error if the config file doesn't exist.
    """

    global config

    if config is None:
        file_ = os.path.join(get_home(), *config_file)

        if not os.path.exists(file_):
            raise Error("Config file {} doesn't exist", file_)

        config = configparser.ConfigParser()
        config.read(file_, encoding='utf8')

    return config

# Taken from Hedwig
def get_home():
    """
    Determine the application's home directory.
    """

    global home_directory

    if home_directory is not None:
        return home_directory

    return os.environ.get('PIGWIDGEON_DIR', os.getcwd())




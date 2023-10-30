DB_TOOLS = False


class Config(object):
    """
    Common configurations
    """
    STATIC_PATH = "app/static"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    LOG_LEVEL = "INFO"
    PRESERVE_CONTEXT_ON_EXCEPTION = True
    SOCKETIO_ASYNC_MODE = 'gevent'

class DevelopmentConfig(Config):
    """
    Development configurations
    """
    DEBUG = True
    SQLALCHEMY_ECHO = False
    SOCKETIO_ASYNC_MODE = None


class ProductionConfig(Config):
    """
    Production configurations
    """
    DEBUG = False


app_config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig
    }

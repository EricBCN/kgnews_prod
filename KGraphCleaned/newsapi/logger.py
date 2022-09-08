import logging
import logging.config

LOGGER_CFG = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'default': {
            'class': 'logging.StreamHandler',
            'formatter': 'detailed'
        }
    },
    'formatters': {
        'detailed': {
            'format': "%(asctime)s %(levelname)s %(module)s - %(funcName)s:%(lineno)d : %(message)s"
        }
    },
    'loggers': {
        'framework': {
            'level': 'DEBUG',
            'handlers': ['default'],
            'propagate': False
        }
    }
}

__all__ = [
    'logger'
]


def setup_logger():
    """
    Replaces getLogger from logging to ensure each worker configures logging locally
    :param name: name which will be set to the logger
    :return: logger working instance.
    """
    # Set the base config from the constants dict
    logging.config.dictConfig(LOGGER_CFG)
    return logging.getLogger('framework')


logger = setup_logger()

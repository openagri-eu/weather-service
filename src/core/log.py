import logging
import logging.config


def setup_logging(level: str):
    # Disable noisy logging
    logging.getLogger('pymongo').setLevel(logging.WARNING)

    logging_config = {
        'version': 1,
        'disable_existing_loggers': False,
        'loggers': {
            '': {
                'handlers': ['console'],
                'level': level,
            },
        },
        'formatters': {
            'default': {
                'format': (
                    '%(levelname)s %(name)s [%(asctime)s.%(msecs)03d] '
                    '%(filename)s:%(lineno)s %(message)s'
                ),
                'datefmt': '%Y-%m-%d %H:%M:%S',
            },
        },
        'handlers': {
            'console': {
                'level': level,
                'class': 'logging.StreamHandler',
                'stream': 'ext://sys.stdout',
                'formatter': 'default',
            },
        },
    }

    logging.config.dictConfig(logging_config)

import os
import logging
import errno


def setup_logging():
    lvl = logging.DEBUG if os.environ.get('VERBOSE') else logging.INFO
    fmt = '%(asctime)s %(message)s'
    datefmt = '%Y/%m/%d %H:%M:%S'
    logging.basicConfig(level=lvl, format=fmt, datefmt=datefmt)


def handle_env():
    envs = ['VERBOSE', 'REDIS_URL', 'ROUTING_STORE', 'GAME_PORT']
    config = {k: v for k, v in os.environ.items() if k in envs}

    if not config.get('REDIS_URL'):
        logging.critical("No Redis url given. Exiting")
        exit(errno.EINVAL)

    if not config.get('ROUTING_STORE'):
        logging.critical('No Routing table specified. Exiting')
        exit(errno.EINVAL)

    if not config.get('GAME_PORT'):
        logging.critical('No game port env variable. Exiting')
        exit(errno.EINVAL)
    return config

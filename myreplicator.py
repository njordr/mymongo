import logging
import logging.handlers
import configparser

from mymongolib import utils
from mymongolib import mysql
from mymongolib.mongodb import MyMongoDB

config = configparser.ConfigParser()
config.read('config.ini')

logger = logging.getLogger('mymongo')
logger.setLevel(logging.getLevelName(config['log']['console_level']))
logformatter = logging.Formatter('%(asctime)s;%(levelname)s;%(message)s')
fh = logging.handlers.TimedRotatingFileHandler('logs/mymongo.log', 'midnight', 1, backupCount=10)
fh.setLevel(logging.getLevelName(config['log']['file_level']))
fh.setFormatter(logformatter)
ch = logging.StreamHandler()
ch.setLevel(logging.getLevelName(config['log']['console_level']))
ch.setFormatter(logformatter)
logger.addHandler(fh)
logger.addHandler(ch)

if __name__ == '__main__':
    logger.info('Start mymongo')
    mongo = MyMongoDB(config['mongodb'])
    mysql.mysql_stream(config['mysql'], mongo)
#!/usr/bin/env python3

import logging
import logging.handlers
import configparser
import sys
import socket
import logging.config


from mymongolib import utils
from mymongolib.mongodb import MyMongoDB
from mymongolib.mymongodaemon import MyMongoDaemon
from mymongolib.utils import LoggerWriter


config = configparser.ConfigParser()
config.read('conf/config.ini')

logging.config.fileConfig('conf/logging.conf')
logger = logging.getLogger('root')

hostname = socket.gethostname()

if __name__ == '__main__':
    logger.info('Start mymongo')
    parser = utils.cmd_parser()
    args = parser.parse_args()
    mongo = MyMongoDB(config['mongodb'])
    if args.mysqldump_data:
        try:
            utils.run_mysqldump(dump_type='data', conf=config['mysql'], mongodb=mongo)
            logger.info('Data dump procedure ended')
            sys.exit(0)
        except Exception as e:
            logger.error('Data dump procedure ended with errors: ' + str(e))
            sys.exit(1)
    elif args.mysqldump_schema:
        try:
            utils.run_mysqldump(dump_type='schema', conf=config['mysql'], mongodb=mongo)
            logger.info('Schema dump procedure ended')
            sys.exit(0)
        except Exception as e:
            logger.error('Schema dump procedure ended with errors: ' + str(e))
            sys.exit(1)
    elif args.mysqldump_complete:
        try:
            utils.run_mysqldump(dump_type='complete', conf=config['mysql'], mongodb=mongo)
            logger.info('Complete dump procedure ended')
            sys.exit(0)
        except Exception as e:
            logger.error('Complete dump procedure ended with errors: ' + str(e))
            sys.exit(1)

    log_err = LoggerWriter(logger, logging.ERROR)
    mymongo_daemon = MyMongoDaemon(config['general']['pid_file'], log_err=log_err)
    if args.start:
        for db in config['mysql']['databases'].split(','):
            parsed = mongo.get_db_as_parsed(db)
            if parsed is None:
                logger.error('Database schema ' + db + ' has not been parsed. Please run schema dump procedure before')
                sys.exit(1)
            elif parsed['schema'] == 'ko':
                logger.error('Database schema ' + db + ' has not been parsed. Please run schema dump procedure before')
                sys.exit(1)
            elif parsed['data'] == 'ko':
                logger.warning('Database data ' + db + ' has not been parsed. '
                                                       'It could be better to run data dump procedure before')

        mymongo_daemon.start()
    elif args.stop:
        mymongo_daemon.stop()
    elif args.restart:
        mymongo_daemon.restart()
    elif args.status:
        mymongo_daemon.status()
    sys.exit(0)


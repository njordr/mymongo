import signal
import sys
import logging

from pymysqlreplication import BinLogStreamReader
from importlib import util
from pymysqlreplication.row_event import (
    DeleteRowsEvent,
    UpdateRowsEvent,
    WriteRowsEvent,
)

logger = logging.getLogger('mymongo')


def mysql_stream(conf, mongo):
    # server_id is your slave identifier, it should be unique.
    # set blocking to True if you want to block and wait for the next event at
    # the end of the stream
    mysql_settings = {
        "host": conf['host'],
        "port": conf.getint('port'),
        "user": conf['user'],
        "passwd": conf['password']
    }

    # Tries to close the stream and unoccupy the database upon getting
    # SIGTERM, SIGABRT, or SIGINT. On SIGINT, it won't exit the
    # program, but on SIGTERM and SIGABRT it will.

    def signal_handler(signum, frame):
        logger.debug('killed')
        # TODO manage connection close
        #close_connections(memsql_conn, stream)
        sys.exit(1)
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGABRT, signal_handler)

    try:
        util.find_spec('setproctitle')
        import setproctitle
        setproctitle.setproctitle('mymongo_mysql_replicator')
    except ImportError:
        logger.info('Cannot set process name')

    last_log = mongo.get_log_pos()
    if last_log['log_file'] == 'NA':
        log_file = None
        log_pos = None
        resume_stream = False
    else:
        log_file = last_log['log_file']
        log_pos = int(last_log['log_pos'])
        resume_stream = True

    stream = BinLogStreamReader(connection_settings=mysql_settings,
                                server_id=conf.getint('slaveid'),
                                only_events=[DeleteRowsEvent, WriteRowsEvent, UpdateRowsEvent],
                                blocking=True,
                                resume_stream=resume_stream,
                                log_file=log_file,
                                log_pos=log_pos,
                                only_schemas=conf['databases'].split(','))

    for binlogevent in stream:
        binlogevent.dump()
        schema = "%s" % binlogevent.schema
        table = "%s" % binlogevent.table

        for row in binlogevent.rows:
            if isinstance(binlogevent, DeleteRowsEvent):
                vals = row["values"]
                event_type = 'delete'
            elif isinstance(binlogevent, UpdateRowsEvent):
                vals = row["after_values"]
                event_type = 'update'
            elif isinstance(binlogevent, WriteRowsEvent):
                vals = row["values"]
                event_type = 'insert'

            mongo.write_to_queue(event_type, vals, schema, table)
            mongo.write_log_pos(stream.log_file, stream.log_pos)
            logger.debug(row)
            logger.debug(stream.log_pos)
            logger.debug(stream.log_file)

    stream.close()


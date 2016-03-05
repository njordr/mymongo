import signal
import sys
import logging

from pymysqlreplication import BinLogStreamReader
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

    stream = BinLogStreamReader(connection_settings=mysql_settings,
                                server_id=conf.getint('slaveid'),
                                only_events=[DeleteRowsEvent, WriteRowsEvent, UpdateRowsEvent],
                                blocking=True)

    for binlogevent in stream:
        binlogevent.dump()
        prefix = "%s:%s:" % (binlogevent.schema, binlogevent.table)

        for row in binlogevent.rows:
            if isinstance(binlogevent, DeleteRowsEvent):
                vals = row["values"]
                #r.delete(prefix + str(vals["id"]))
            elif isinstance(binlogevent, UpdateRowsEvent):
                vals = row["after_values"]
                #r.hmset(prefix + str(vals["id"]), vals)
            elif isinstance(binlogevent, WriteRowsEvent):
                vals = row["values"]
                logger.debug(mongo.get_next_seqnum('insert_seq'))
                #r.hmset(prefix + str(vals["id"]), vals)
            logger.debug(vals)

    stream.close()


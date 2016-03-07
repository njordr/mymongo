import argparse
import logging
import subprocess
import os

from tempfile import NamedTemporaryFile


logger = logging.getLogger('mymongo')


def cmd_parser():
    parser = argparse.ArgumentParser(description='Replicate a MySQL database to MongoDB')
    parser.add_argument('--resume-from-end', dest='resume_from_end',
                        action='store_true', help="Even if the binlog\
                        replication was interrupted, start from the end of\
                        the current binlog rather than resuming from the interruption",
                        default=False)
    parser.add_argument('--resume-from-start', dest='resume_from_start',
                        action='store_true', help="Start from the beginning\
                        of the current binlog, regardless of the current position", default=False)
    parser.add_argument('--mysqldump-file', dest='mysqldump_file', type=str,
                        help='Specify a file to get the mysqldump from, rather\
                        than having ditto running mysqldump itself',
                        default='')
    parser.add_argument('--mysqldump-schema', dest='mysqldump_schema',
                        action='store_true', help="Run mysqldump to create new databases on mongodb, but \
                        not import any data so you can review mmongodb schema before importing data", default=False)
    parser.add_argument('--mysqldump-data', dest='mysqldump_data',
                        action='store_true', help="Run mysqldump to import only data", default=False)
    parser.add_argument('--mysqldump-complete', dest='mysqldump_complete',
                        action='store_true', help="Run mysqldump to create new databases and import data", default=False)

    return parser


def run_mysqldump(dump_type, conf):
    for db in conf['databases'].split(','):
        mysqldump_cmd(conf, db, dump_type=dump_type)
    return True


def mysqldump_cmd(conf, db, dump_type):
    dump_file = NamedTemporaryFile(delete=False)
    dumpcommand = ['mysqldump',
                    '--user=' + conf['user'],
                    '--host=' + conf['host'],
                    '--port=' + conf['port'],
                    '--force',
                    '--xml',
                    '--master-data=2']
    if conf['password'] != '':
        dumpcommand.append('--password=' + conf['password'])
    if dump_type == 'schema':
        dumpcommand.append('--no-data')
    elif dump_type == 'data':
        dumpcommand.append('--no-create-db')
        dumpcommand.append('--no-create-info')
    dumpcommand.append(db)

    logger.debug('executing: {0}'.format(' '.join(dumpcommand)))

    with open(dump_file.name, 'wb', 0) as f:
        p1 = subprocess.Popen(dumpcommand, stdout=f)
    p1.wait()

    # TODO enable temp file delete
    # os.unlink(dump_file.name)

    # TODO save log_pos to mongo to start from here with replicator

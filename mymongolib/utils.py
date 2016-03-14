import argparse
import logging
import subprocess
import os
import re

from tempfile import NamedTemporaryFile
from lxml import etree
from .exceptions import SysException


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
    # parser.add_argument('--mysqldump-schema', dest='mysqldump_schema',
    #                    action='store_true', help="Run mysqldump to create new databases on mongodb, but \
    #                    not import any data so you can review mmongodb schema before importing data", default=False)
    parser.add_argument('--mysqldump-data', dest='mysqldump_data',
                        action='store_true', help="Run mysqldump to import only data", default=False)
    # parser.add_argument('--mysqldump-complete', dest='mysqldump_complete',
    #                    action='store_true', help="Run mysqldump to create new databases and import \
    #                   data", default=False)
    parser.add_argument('--daemon', dest='daemon',
                        action='store_true', help="Start the daemon process", default=False)
    return parser


def run_mysqldump(dump_type, conf, mongodb):
    for db in conf['databases'].split(','):
        try:
            dump_file = mysqldump_cmd(conf, db, dump_type=dump_type)
        except Exception as e:
            raise SysException(e)

        try:
            mysqldump_parser_data(dump_file, mongodb)
        except Exception as e:
            raise SysException(e)

    return True


def process_data_buffer(buf, table, db, mongodb):
    parser = etree.XMLParser(recover=True)
    tnode = etree.fromstring(buf, parser=parser)
    doc = dict()
    for child in tnode:
        if child.tag == 'field':
            doc[child.attrib['name']] = child.text

    try:
        mongodb.insert(doc, db, table)
    except Exception as e:
        raise SysException(e)

    del tnode


def mysqldump_parser_data(dump_file, mongodb):
    inputbuffer = ''
    db_start = re.compile(r'.*<database name.*', re.IGNORECASE)
    tb_start = re.compile(r'.*<table_data.*', re.IGNORECASE)
    row_start = re.compile(r'.*<row>.*', re.IGNORECASE)
    row_end = re.compile(r'.*</row>.*', re.IGNORECASE)
    master_log = re.compile(r'.*CHANGE MASTER.*', re.IGNORECASE)
    db = ''
    table = ''
    log_file = None
    log_pos = None

    with open(dump_file, 'r') as inputfile:
        append = False
        for line in inputfile:
            if row_start.match(line):
                # print('start')
                inputbuffer = line
                append = True
            elif row_end.match(line):
                # print('end')
                inputbuffer += line
                append = False
                process_data_buffer(inputbuffer, table, db, mongodb)
                inputbuffer = None
                del inputbuffer
            elif append:
                # print('elif')
                inputbuffer += line
            elif db_start.match(line):
                db = re.findall('name="(.*?)"', line, re.DOTALL)[0]
                try:
                    mongodb.drop_db(db)
                except Exception as e:
                    raise SysException(e)
            elif tb_start.match(line):
                table = re.findall('name="(.*?)"', line, re.DOTALL)[0]
            elif master_log.match(line):
                log_file = re.findall("MASTER_LOG_FILE='(.*?)'", line, re.DOTALL)[0]
                log_pos = re.findall("MASTER_LOG_POS=(.*?);", line, re.DOTALL)[0]

    if log_file is not None and log_pos is not None:
        try:
            mongodb.write_log_pos(log_file, log_pos)
        except Exception as e:
            raise SysException(e)


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
        try:
            p1 = subprocess.Popen(dumpcommand, stdout=f)
        except Exception as e:
            raise SysException(e)
    p1.wait()

    return dump_file.name

    # TODO save log_pos to mongo to start from here with replicator

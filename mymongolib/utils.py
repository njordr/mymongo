import argparse


def cmd_parser():
    parser = argparse.ArgumentParser(description='Replicate a MySQL database to MongoDB')
    parser.add_argument('database', help='Database to use')
    parser.add_argument('--mysql-host', dest='mysql_host', type=str,
                        help='MySQL database server',
                        default='127.0.0.1')
    parser.add_argument('--mysql-user', dest='mysql_user', type=str,
                        help='MySQL Username', default='root')
    parser.add_argument('--mysql-password', dest='mysql_password', type=str,
                        help='MySQL Password', default='')
    parser.add_argument('--mysql-port', dest='mysql_port', type=int,
                        help='MySQL port', default=3306)
    parser.add_argument('--mysql-slaveid', dest='mysql_slaveid', type=int,
                        help='MySQL slave id (must be unique in your replication servers)', default=3)
    parser.add_argument('--mongodb-host', dest='mongodb_host', type=str,
                        help='MongoDB database server',
                        default='127.0.0.1')
    parser.add_argument('--mongodb-user', dest='mongo_user', type=str,
                        help='MongoDB Username', default='')
    parser.add_argument('--mongodb-password', dest='mongo_password', type=str,
                        help='MongoDB password', default='')
    parser.add_argument('--mongodb-port', dest='mongo_port', type=int,
                        help='MongoDB port', default=27017)
    parser.add_argument('--no-dump', dest='no_dump', action='store_true',
                        help="Don't run mysqldump before reading\
                        (expects schema to already be set up)", default=False)
    parser.add_argument('--resume-from-end', dest='resume_from_end',
                        action='store_true', help="Even if the binlog\
                        replication was interrupted, start from the end of\
                        the current binlog rather than resuming from the interruption",
                        default=False)
    parser.add_argument('--resume-from-start', dest='resume_from_start',
                        action='store_true', help="Start from the beginning\
                        of the current binlog, regardless of the current position", default=False)
    parser.add_argument('--log', dest='loglevel', type=str,
                        help="Set the logging verbosity with one of the\
                        following options (in order of increasing verbosity):\
                        DEBUG, INFO, WARNING, ERROR, CRITICAL", default="DEBUG")
    parser.add_argument('--mysqldump-file', dest='mysqldump_file', type=str,
                        help='Specify a file to get the mysqldump from, rather\
                        than having ditto running mysqldump itself',
                        default='')
    return parser

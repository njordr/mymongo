import pymongo
import urllib.parse
import logging

from .exceptions import SysException
from pymongo.errors import CollectionInvalid
from datetime import datetime

# logger = logging.getLogger(__name__)


class MyMongoDB:
    mdb = None
    utildb = ''
    checked_colls = []

    def __init__(self, conf):
        self.logger = logging.getLogger(__name__)
        try:
            password = urllib.parse.quote(conf['password'])
        except Exception as e:
            raise SysException(e)

        if conf['user'] == '':
            conn_string = 'mongodb://' + \
                            conf['host'] + ':' + \
                            conf['port'] + '/'
        else:
            conn_string = 'mongodb://' + \
                            conf['user'] + ':' + \
                            password + '@' + \
                            conf['host'] + ':' + \
                            conf['port'] + '/'
        try:
            self.mdb = pymongo.MongoClient(conn_string, connect=False)
        except Exception as e:
            raise SysException(e)
        self.utildb = conf['utildb']

    def get_db(self, db_name):
        try:
            db = self.mdb[db_name]
        except:
            try:
                db = self.mdb.get_database(db_name)
            except Exception as e:
                raise SysException(e)

        return db

    def get_coll(self, coll_name, db_name):
        new = False
        db = None

        try:
            db = self.get_db(db_name)
        except Exception as e:
            SysException(e)

        if coll_name not in self.checked_colls:
            try:
                db.create_collection(coll_name)
                new = True
            except CollectionInvalid as e:
                self.logger.info(str(e))
            except Exception as e:
                raise SysException(e)

            self.checked_colls.append(coll_name)

        coll = db[coll_name]

        if new:
            if coll_name == 'counters':
                try:
                    coll.insert_one({'_id': 'insert_seq', 'num': 0})
                    coll.insert_one({'_id': 'update_seq', 'num': 0})
                    coll.insert_one({'_id': 'delete_seq', 'num': 0})
                except Exception as e:
                    raise SysException(e)
            elif coll_name == 'mysqllog':
                try:
                    coll.insert_one({'_id': 'last_log_pos', 'log_file': 'NA', 'log_pos': 'NA'})
                except Exception as e:
                    raise SysException(e)

        return coll

    def get_next_seqnum(self, seq_name):
        coll = self.get_coll('counters', self.utildb)
        try:
            seq = coll.find_one({'_id': seq_name})
        except Exception as e:
            raise SysException(e)
        try:
            coll.replace_one({'_id': seq_name}, {'num': seq['num'] + 1})
        except Exception as e:
            raise SysException(e)

        return seq['num']

    def write_log_pos(self, log_file, log_pos):
        coll = self.get_coll('mysqllog', self.utildb)
        try:
            coll.replace_one({'_id': 'last_log_pos'}, {'log_file': log_file, 'log_pos': log_pos})
        except Exception as e:
            raise SysException(e)

    def get_log_pos(self):
        coll = self.get_coll('mysqllog', self.utildb)
        try:
            last_log = coll.find_one({'_id': 'last_log_pos'})
        except Exception as e:
            raise SysException(e)

        return last_log

    def write_to_queue(self, event_type, values, schema, table):
        seqnum = datetime.now().timestamp()
        if event_type == 'insert':
            # coll = self.get_coll('insert_queue', self.utildb)
            coll = self.get_coll('replicator_queue', self.utildb)
        elif event_type == 'update':
            # coll = self.get_coll('update_queue', self.utildb)
            coll = self.get_coll('replicator_queue', self.utildb)
        elif event_type == 'delete':
            # coll = self.get_coll('delete_queue', self.utildb)
            coll = self.get_coll('replicator_queue', self.utildb)

        doc = dict()
        doc['schema'] = schema
        doc['table'] = table
        doc['event_type'] = event_type
        doc['seqnum'] = seqnum
        doc['values'] = values

        try:
            coll.insert_one(doc)
        except Exception as e:
            raise SysException(e)

        return seqnum

    def insert(self, doc, schema, collection):
        coll = self.get_coll(collection, schema)

        try:
            coll.insert_one(doc)
        except Exception as e:
            raise SysException(e)

    def update(self, doc, schema, collection, primary_key):
        coll = self.get_coll(collection, schema)

        try:
            coll.replace_one(primary_key, doc)
        except Exception as e:
            raise SysException(e)

    def delete(self, schema, collection, doc=None, primary_key=None):
        coll = self.get_coll(collection, schema)

        if primary_key is None:
            try:
                coll.delete_one(doc)
            except Exception as e:
                raise SysException(e)
        else:
            try:
                self.logger.debug('try to delete doc with key: ' + str(primary_key))
                result = coll.delete_one(primary_key)
                self.logger.debug('delete result: ' + str(result.deleted_count))
            except Exception as e:
                raise SysException(e)

    def delete_from_queue(self, queue_id):
        coll = self.get_coll('replicator_queue', self.utildb)

        try:
            result = coll.delete_one(queue_id)
        except Exception as e:
            raise SysException(e)

    def drop_db(self, db_name):
        if db_name in self.mdb.database_names():
            try:
                self.mdb.drop_database(db_name)
            except Exception as e:
                raise SysException(e)

    def get_from_queue(self, batch_size):
        coll = self.get_coll('replicator_queue', self.utildb)
        try:
            queue = coll.find().sort('seqnum', 1)[0:batch_size]
        except Exception as e:
            raise SysException(e)

        return queue

    def insert_primary_key(self, doc):
        coll = self.get_coll('primary_keys', self.utildb)
        try:
            coll.replace_one({'_id': doc['_id']}, doc, True)
        except Exception as e:
            raise SysException(e)

    def get_primary_key(self, table, db):
        coll = self.get_coll('primary_keys', self.utildb)
        primary = None
        try:
            self.logger.debug('Try to retrieve primary key: ' + db + '.' + table)
            primary = coll.find_one({'_id': db + '.' + table})
        except Exception as e:
            raise SysException(e)

        return primary

    def make_db_as_parsed(self, db, parse_type):
        coll = self.get_coll('parsed_db', self.utildb)
        try:
            doc = coll.find_one({'_id': db})
        except Exception as e:
            raise SysException(e)

        if doc is None:
            doc = dict()
            doc['_id'] = db
            doc['db'] = db
            doc['schema'] = 'ko'
            doc['data'] = 'ko'

        if parse_type == 'schema':
            doc['schema'] = 'ok'
        elif parse_type == 'data':
            doc['data'] = 'ok'

        try:
            coll.replace_one({'_id': db}, doc, True)
        except Exception as e:
            raise SysException(e)

    def get_db_as_parsed(self, db):
        coll = self.get_coll('parsed_db', self.utildb)

        try:
            doc = coll.find_one({'_id': db})
        except Exception as e:
            raise SysException(e)

        return doc

import pymongo
import urllib.parse
import logging

from .exceptions import SysException

logger = logging.getLogger('mymongo')


class MyMongoDB:
    mdb = None
    utildb = ''

    def __init__(self, conf):
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
            self.mdb = pymongo.MongoClient(conn_string)
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

    def get_coll(self, coll_name):
        new = False
        db = None

        try:
            db = self.get_db(self.utildb)
        except Exception as e:
            SysException(e)

        try:
            db.create_collection(coll_name)
            new = True
        except Exception as e:
            logger.info('Error creating collection: ' + str(e))
        coll = db[coll_name]
        if new:
            if coll_name == 'counters':
                try:
                    coll.insert_one({'_id': 'insert_seq', 'num': 0})
                    coll.insert_one({'_id': 'update_seq', 'num': 0})
                    coll.insert_one({'_id': 'delete_seq', 'num': 0})
                except Exception as e:
                    raise SysException(e)

        return coll

    def get_next_seqnum(self, seq_name):
        coll = self.get_coll('counters')
        logger.debug('seq_name: ' + seq_name)
        seq = coll.find_one({'_id': seq_name})
        logger.debug('doc: ')
        logger.debug(seq)
        coll.replace_one({'_id': seq_name}, {'num': seq['num'] + 1})

        return seq['num']

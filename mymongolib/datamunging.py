import logging
import time


class DataMunging:
    mongo = None

    def __init__(self, mongo):
        self.mongo = mongo
        self.logger = logging.getLogger(__name__)

    def run(self, module_instance=None):
        while True:
            self.logger.info('data munging')
            try:
                queue = self.mongo.get_from_queue(100)
            except Exception as e:
                self.logger.error('Cannot get entries from replicator queue. Error: ' + str(e))

            to_delete = list()
            for record in queue:
                if module_instance is not None:
                    try:
                        doc = module_instance.run(record, self.mongo)
                    except Exception as e:
                        self.logger.error('Error during parse data with module. Erro: ' + str(e))
                        doc = record

                    key = None
                    if doc['event_type'] in ['update', 'delete']:
                        try:
                            key = self.mongo.get_primary_key(doc['schema'], doc['table'])
                        except Exception as e:
                            self.logger.error('Cannot get primary key for table ' + doc['table'] +
                                              ' in schema ' + doc['schema'] + '. Error: ' + str(e))

                    if doc['event_type'] == 'insert':
                        try:
                            self.mongo.insert(doc['values'], doc['schema'], doc['table'])
                            to_delete.append(str(doc['_id']))
                        except Exception as e:
                            self.logger.error('Cannot insert document into collection ' + doc['table'] +
                                              ' db ' + doc['schema'] + ' Error: ' + str(e))
                    elif doc['event_type'] == 'update':
                        if key is None:
                            self.logger.error('Cannot update document ' + str(doc['_id']) + ' without a primary key')
                            continue
                        primary_key = dict()
                        for k in key['primary_key']:
                            primary_key[k] = doc['values'][k]
                        try:
                            self.mongo.update(doc['values'], doc['schema'], doc['table'], primary_key)
                            to_delete.append(doc['_id'])
                        except Exception as e:
                            self.logger.error('Cannot update document ' + str(doc['_id']) +
                                              ' into collection ' + doc['table'] +
                                              ' db ' + doc['schema'] + ' Error: ' + str(e))
                    elif doc['event_type'] == 'delete':
                        if key is not None:
                            primary_key = dict()
                            for k in key['primary_key']:
                                primary_key[k] = doc['values'][k]
                        else:
                            primary_key = None

                        try:
                            self.mongo.delete(doc['values'], doc['schema'], doc['table'], primary_key)
                            to_delete.append(doc['_id'])
                        except Exception as e:
                            self.logger.error('Cannot delete document ' + str(doc['_id']) +
                                              ' into collection ' + doc['table'] +
                                              ' db ' + doc['schema'] + ' Error: ' + str(e))

                self.logger.debug(record)


            time.sleep(60)

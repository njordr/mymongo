import logging
import time
import threading


class DataMunging:
    mongo = None

    def __init__(self, mongo, replicator_queue):
        self.mongo = mongo
        self.logger = logging.getLogger(__name__)
        self.replicator_queue = replicator_queue
        self.lock = threading.Lock()
        self.last_seqnum = 0
        self.run_parser = False

    def run(self, module_instance=None):

        queue_thread = threading.Thread(target=self.check_queue)
        queue_thread.daemon = True
        queue_thread.start()

        while True:
            time.sleep(.1)

            try:
                queue = self.mongo.get_from_queue(100)
            except Exception as e:
                self.logger.error('Cannot get entries from replicator queue. Error: ' + str(e))

            if queue.count() < 1:
                self.logger.debug('No entries in replicator queue')
                if not self.run_parser:
                    self.logger.debug('No messages from replicator queue')
                    continue

            to_delete = list()
            for record in queue:
                if module_instance is not None:
                    try:
                        doc = module_instance.run(record, self.mongo)
                    except Exception as e:
                        self.logger.error('Error during parse data with module. Error: ' + str(e))
                        doc = record

                key = None
                self.logger.debug('Event: ' + doc['event_type'])
                if doc['event_type'] in ['update', 'delete']:
                    self.logger.debug('Event: ' + doc['event_type'])
                    try:
                        key = self.mongo.get_primary_key(doc['table'], doc['schema'])
                        self.logger.debug(key)
                    except Exception as e:
                        self.logger.error('Cannot get primary key for table ' + doc['table'] +
                                          ' in schema ' + doc['schema'] + '. Error: ' + str(e))

                if doc['event_type'] == 'insert':
                    try:
                        self.mongo.insert(doc['values'], doc['schema'], doc['table'])
                        to_delete.append(str(doc['_id']))
                        self.last_seqnum = doc['seqnum']
                    except Exception as e:
                        self.logger.error('Cannot insert document into collection ' + doc['table'] +
                                          ' db ' + doc['schema'] + ' Error: ' + str(e))
                elif doc['event_type'] == 'update':
                    if key is None:
                        self.logger.error('Cannot update document ' + str(doc['_id']) + ' without a primary key')
                        continue
                    primary_key = dict()
                    for k in key['primary_key']:
                        primary_key[k] = str(doc['values'][k])
                    try:
                        self.mongo.update(doc['values'], doc['schema'], doc['table'], primary_key)
                        to_delete.append(doc['_id'])
                        self.last_seqnum = doc['seqnum']
                    except Exception as e:
                        self.logger.error('Cannot update document ' + str(doc['_id']) +
                                          ' into collection ' + doc['table'] +
                                          ' db ' + doc['schema'] + ' Error: ' + str(e))
                elif doc['event_type'] == 'delete':
                    if key is not None:
                        primary_key = dict()
                        for k in key['primary_key']:
                            primary_key[k] = str(doc['values'][k])
                    else:
                        primary_key = None

                    try:
                        self.mongo.delete(doc=doc['values'], schema=doc['schema'], collection=doc['table'],
                                          primary_key=primary_key)
                        to_delete.append(doc['_id'])
                        self.last_seqnum = doc['seqnum']
                    except Exception as e:
                        self.logger.error('Cannot delete document ' + str(doc['_id']) +
                                            ' into collection ' + doc['table'] +
                                            ' db ' + doc['schema'] + ' Error: ' + str(e))

            self.logger.debug('Delete records: ' + str(to_delete))
            for queue_id in to_delete:
                try:
                    # self.mongo.delete_from_queue({'_id': queue_id})
                    continue
                except Exception as e:
                    self.logger.error('Cannot delete document from queue Error: ' + str(e))

            time.sleep(5)

    def check_queue(self):
        self.logger.info('Start QueueMonitor')

        while True:
            if not self.replicator_queue.empty():
                try:
                    self.logger.debug('Try to read from replicator queue')
                    msg_queue = self.replicator_queue.get()
                    self.logger.debug('Read from replicator queue')
                    self.manage_replicator_msg(msg_queue)
                    self.logger.debug('Replicator message managed')
                except Exception as e:
                    self.logger.error('Cannot read and manage replicator message. Error: ' + str(e))

            time.sleep(.1)

    def manage_replicator_msg(self, msg):
        with self.lock:
            self.logger.debug('Message from queue')
            self.logger.debug(msg)
            self.logger.debug('Last seqnum: ' + str(self.last_seqnum))
            if msg['seqnum'] > self.last_seqnum:
                self.logger.debug('new entries in queue')
                self.run_parser = True
            else:
                self.logger.debug('NO new entries in queue')
                self.run_parser = False

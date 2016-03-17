import sys
import time
import logging
import os
import configparser

from importlib import util
from multiprocessing import Process
from multiprocessing import Queue
from apscheduler.schedulers.blocking import BlockingScheduler

from mymongolib.daemon import Daemon
from mymongolib import mysql
from mymongolib.mongodb import MyMongoDB
from mymongolib.datamunging import DataMunging
from mymongomodules.parse_data import ParseData
from mymongomodules.process_data import ProcessData

config = configparser.ConfigParser()
config.read('conf/config.ini')


class MyMongoDaemon(Daemon):
    def run(self):
        self.logger = logging.getLogger(__name__)
        sys.stderr = self.log_err
        try:
            util.find_spec('setproctitle')
            self.setproctitle = True
            import setproctitle
            setproctitle.setproctitle('mymongo')
        except ImportError:
            self.setproctitle = False
    
        self.logger.info("Running")

        self.queues = dict()
        self.queues['replicator_out'] = Queue()
        procs = dict()
        procs['scheduler'] = Process(name='scheduler', target=self.scheduler)
        procs['scheduler'].daemon = True
        procs['scheduler'].start()
        procs['replicator'] = Process(name='replicator', target=self.replicator)
        procs['replicator'].daemon = True
        procs['replicator'].start()
        procs['datamunging'] = Process(name='datamunging', target=self.data_munging)
        procs['datamunging'].daemon = True
        procs['datamunging'].start()
        procs['dataprocess'] = Process(name='dataprocess', target=self.data_process)
        procs['dataprocess'].daemon = True
        procs['dataprocess'].start()

        while True:
            self.logger.info('Working...')
            time.sleep(60)

    def scheduler(self):
        self.write_pid(str(os.getpid()))
        if self.setproctitle:
            import setproctitle
            setproctitle.setproctitle('mymongo_scheduler')
        sched = BlockingScheduler()
        try:
            sched.add_job(self.dummy_sched, 'interval', minutes=1)
            sched.start()
        except Exception as e:
            self.logger.error('Cannot start scheduler. Error: ' + str(e))
    
    def dummy_sched(self):
        self.logger.info('Scheduler works!')

    def write_pid(self, pid):
        open(self.pidfile, 'a+').write("{}\n".format(pid))

    def replicator(self):
        self.write_pid(str(os.getpid()))
        if self.setproctitle:
            import setproctitle
            setproctitle.setproctitle('mymongo_replicator')

        mongo = MyMongoDB(config['mongodb'])
        mysql.mysql_stream(config['mysql'], mongo, self.queues['replicator_out'])

    '''
    def start_module(self):
        self.logger.debug('Start ' + self.start_module.__name__)

        mod_base = os.path.join(config['general']['base_dir'], config['general']['mod_base_dir'])
        module_name = config['general']['parse_data_module']
        sys.path.insert(0, mod_base)

        if not os.path.isdir(mod_base):
            self.logger.error('Module dir: ' + mod_base + ' does not exist. Skipping module ' + module_name)

        mod_base_name = os.path.basename(mod_base)
        try:
            self.modules[module_name] = __import__('%s.%s' % (mod_base_name, module_name), fromlist=[module_name])
        except Exception as e:
            self.logger.error('Cannot load module named: ' + module_name + ' Error: ' + str(e))

        try:
            class_ = getattr(self.modules[module_name], module_name)
        except Exception as e:
            self.logger.error('Cannot load class name: ' + module_name + ' from module: ' +
                              str(self.modules[module_name].__name__) + ' Error: ' + str(e))

        try:
            instance = class_()
        except Exception as e:
            self.logger.error('Cannot instantiate class: ' + module_name + ' Error: ' + str(e))

        return instance
    '''
    def data_munging(self):
        self.write_pid(str(os.getpid()))
        if self.setproctitle:
            import setproctitle
            setproctitle.setproctitle('mymongo_datamunging')

        module_instance = ParseData()

        mongo = MyMongoDB(config['mongodb'])
        munging = DataMunging(mongo, self.queues['replicator_out'])
        munging.run(module_instance)

    def data_process(self):
        self.write_pid(str(os.getpid()))
        if self.setproctitle:
            import setproctitle
            setproctitle.setproctitle('mymongo_dataprocess')

        mongo = MyMongoDB(config['mongodb'])
        process_instance = ProcessData(mongo)
        process_instance.run()

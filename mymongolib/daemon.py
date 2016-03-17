import sys
import os
import time
import atexit
import logging

from signal import SIGTERM


class Daemon(object):
    """
    Subclass Daemon class and override the run() method.
    """
    def __init__(self, pidfile, stdin='/dev/null', stdout='/dev/null', stderr='/dev/null', log_err=None):
        self.stdin = stdin
        self.stdout = stdout
        self.stderr = stderr
        self.pidfile = pidfile
        if log_err is not None:
            self.log_err = log_err
        self.logger = logging.getLogger(__name__)
        self.modules = dict()

    def daemonize(self):
        """
        Deamonize, do double-fork magic.
        """
        try:
            pid = os.fork()
            if pid > 0:
                # Exit first parent.
                self.logger.info("Done first fork")
                sys.exit(0)
        except OSError as e:
            message = "Fork #1 failed: {}\n".format(e)
            self.logger.error(message)
            sys.stderr.write(message)
            sys.exit(1)

        # Decouple from parent environment.
        os.chdir("/")
        os.setsid()
        os.umask(0)

        # Do second fork.
        try:
            pid = os.fork()
            if pid > 0:
                # Exit from second parent.
                self.logger.info("Done second fork")
                sys.exit(0)
        except OSError as e:
            message = "Fork #2 failed: {}\n".format(e)
            self.logger.error(message)
            sys.stderr.write(message)
            sys.exit(1)

        self.logger.info('deamon going to background, PID: {}'.format(os.getpid()))

        # Redirect standard file descriptors.
        sys.stdout.flush()
        sys.stderr.flush()
        si = open(self.stdin, 'r')
        so = open(self.stdout, 'a+')
        se = open(self.stderr, 'a+')
        os.dup2(si.fileno(), sys.stdin.fileno())
        os.dup2(so.fileno(), sys.stdout.fileno())
        os.dup2(se.fileno(), sys.stderr.fileno())

        # Write pidfile.
        pid = str(os.getpid())
        open(self.pidfile,'w+').write("{}\n".format(pid))

        # Register a function to clean up.
        atexit.register(self.delpid)

    def delpid(self):
        os.remove(self.pidfile)

    def start(self):
        """
        Start daemon.
        """
        pids = None
        # Check pidfile to see if the daemon already runs.
        try:
            with open(self.pidfile) as f:
                pids = f.readlines()
        except IOError:
            pid = None

        if pids:
            message = "Pidfile {} already exist. Daemon already running?\n".format(self.pidfile)
            self.logger.error(message)
            sys.stderr.write(message)
            sys.exit(1)

        # Start daemon.
        self.daemonize()
        self.logger.info("Demonized. Start run")
        self.run()

    def status(self):
        """
        Get status of daemon.
        """
        try:
            with open(self.pidfile) as f:
                pids = f.readlines()
        except IOError:
            message = "There is not PID file. Daemon is not running\n"
            sys.stderr.write(message)
            sys.exit(1)

        for pid in pids:
            try:
                procfile = open("/proc/{}/status".format(pid), 'r')
                procfile.close()
                message = "There is a process with the PID {}\n".format(pid)
                sys.stdout.write(message)
            except IOError:
                message = "There is not a process with the PID {}\n".format(self.pidfile)
                sys.stdout.write(message)

    def stop(self):
        """
        Stop the daemon.
        """
        # Get the pid from pidfile.
        try:
            with open(self.pidfile) as f:
                pids = f.readlines()
        except IOError as e:
            message = str(e) + "\nDaemon not running?\n"
            sys.stderr.write(message)
            self.logger.error(message)
            sys.exit(1)

        for pid in pids:
            # Try killing daemon process.
            try:
                logging.info('Trying to kill pid: '+pid.strip())
                os.kill(int(pid.strip()), SIGTERM)
                self.logger.info('Killed pid: '+pid.strip())
                time.sleep(1)
            except OSError as e:
                self.logger.error('Cannot kill process with pid: '+pid.strip())
                self.logger.error(str(e))
            # sys.exit(1)

        try:
            if os.path.exists(self.pidfile):
                os.remove(self.pidfile)
        except IOError as e:
            message = str(e) + "\nCan not remove pid file {}".format(self.pidfile)
            sys.stderr.write(message)
            self.logger.error(message)
            sys.exit(1)

    def restart(self):
        """
        Restart daemon.
        """
        self.stop()
        time.sleep(1)
        self.start()

    def run(self):
        """
        You should override this method when you subclass Daemon.
        It will be called after the process has been daemonized by start() or restart().

        Example:

        class MyDaemon(Daemon):
            def run(self):
                while True:
                    time.sleep(1)
        """

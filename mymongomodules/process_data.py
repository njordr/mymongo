import time


class ProcessData:
    def __init__(self, mongo):
        self.mongo = mongo

    def run(self):
        while True:
            time.sleep(60)

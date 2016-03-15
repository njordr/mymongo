class ParseData:
    def __call__(self, *args, **kwargs):
        return True

    def run(self, doc, mongo):
        return doc

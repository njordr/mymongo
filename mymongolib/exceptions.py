
class SysException(Exception):
    """Custom exception class

    Args:
        *args: the same as exception class
        **kwargs: the same as exception class

    """
    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)

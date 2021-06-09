import logging


class BaseModule:
    @classmethod
    def config(cls):
        return {}

    @classmethod
    def deps(cls):
        return {}

    def __init__(self, opt):
        self.opt = opt
        self.logger = logging.getLogger(__name__)

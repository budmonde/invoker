#!/usr/bin/env python
from invoker import Workflow

class __WORKFLOW__(Workflow):
    @classmethod
    def args(cls):
        # Specify arguments to pass from command line
        return {}

    @classmethod
    def buid_script_args(cls, args):
        # Args post-processing prior to passing them to each script
        arg_dict = {}
        for script in cls.scripts():
            arg_dict[script] = {}
        return arg_dict

    @classmethod
    def scripts(cls):
        # Add list of scripts to run in sequence
        return []

if __name__ == "__main__":
    __WORKFLOW__().run()

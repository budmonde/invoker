#!/usr/bin/env python
from invoker import Script


class __SCRIPT__(Script):
    @classmethod
    def args(cls):
        # Specify arguments to pass from command line
        return {}

    @classmethod
    def modules(cls):
        return {
            # Add module dependencies
            # "module": "mode"
        }

    @classmethod
    def build_config(cls, args):
        # Args post-processing prior to script main exec
        args.update({
            # Add path keyword to store output
            # "path": "./io/output_path",
        })
        return args

    def run(self):
        # Main logic here
        pass


if __name__ == "__main__":
    __SCRIPT__().initialize().run()

#!/usr/bin/env python
import logging

from invoker import Script


class __SCRIPT__(Script):
    @classmethod
    def args(cls):
        args = super().args()
        args.update(dict(
            # Specify arguments to pass from command line
        ))
        return args

    @classmethod
    def modules(cls):
        mods = super().modules()
        mods.update(dict(
            # Add module dependencies
            # module="mode"
        ))
        return mods

    @classmethod
    def build_config(cls, args):
        # Args post-processing prior to script main exec
        configs = super().build_config(args)
        configs.update(dict(
            # Add path keyword to store output
            # path="./io/output_path",
        ))
        return configs

    def run(self):
        logging.info("Running script __SCRIPT__")
        pass


if __name__ == "__main__":
    __SCRIPT__().initialize().run()

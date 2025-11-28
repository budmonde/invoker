#!/usr/bin/env python
from invoker import InvokerScript


class __SCRIPT__(InvokerScript):
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
            # Import module classes at the top of the file, then add them here:
            # my_module_instance=MyModuleClass
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
        super().run()
        pass


if __name__ == "__main__":
    __SCRIPT__(run_as_root_script=True).run()



from invoker import InvokerModule


class Base__MODULE__(InvokerModule):
    @classmethod
    def args(cls):
        args = super().args()
        args.update(
            dict(
                # Specify arguments to pass from command line
            )
        )
        return args

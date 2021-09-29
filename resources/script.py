from options import build as build_options


def args():
    # Specify arguments to pass from command line
    return {
        # Add path keyword to store output
        # "path": "./output_path",
    }


def build_config(args):
    # Args post-processing prior to script main exec
    return args


def main(opt):
    # Main logic here
    pass


if __name__ == "__main__":
    opt = build_options(mode="script")
    main(opt)

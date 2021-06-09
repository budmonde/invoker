from importlib import resources
import hashlib


def _compute_hash(string):
    hasher = hashlib.md5()
    hasher.update(string)
    return hasher.hexdigest()


def compute_resource_hash(resource_fn):
    with resources.open_binary("resources", resource_fn) as f:
        return _compute_hash(f.read())


def compute_file_hash(path):
    with open(path, "r") as f:
        stored_hash = f.readline().strip().split(" ")[1]
        computed_hash = _compute_hash(f.read().encode('ascii'))
    return stored_hash, computed_hash


def copy_resource(src_fn, dst_path, sign=False, preprocess_fn=lambda l: l):
    with resources.open_binary("resources", src_fn) as f:
        file_hash = _compute_hash(f.read())
    with resources.open_text("resources", src_fn) as inf, open(dst_path, "w") as outf:
        if sign:
            outf.write(f"# {file_hash}\n")
        for line in inf:
            outf.write(preprocess_fn(line))


def to_camel_case(string):
    return "".join([token.capitalize() for token in string.split("_")])

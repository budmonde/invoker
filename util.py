from datetime import date
from importlib import metadata
from pathlib import Path
import hashlib


def _compute_hash(string):
    hasher = hashlib.md5()
    hasher.update(string)
    return hasher.hexdigest()


def _get_resources_path():
    return Path(__file__).parent / "resources"


def compute_resource_hash(resource_fn):
    resource_files = _get_resources_path()
    with (resource_files / resource_fn).open('rb') as f:
        return _compute_hash(f.read())


def compute_file_hash(path):
    with open(path, "r") as f:
        while True:
            hash_line = f.readline()
            if hash_line.startswith("# Hash:"):
                break
        stored_hash = hash_line.strip().split("\t")[1]
        computed_hash = _compute_hash(f.read().encode('ascii'))
    return stored_hash, computed_hash


GENERATED_MESSAGE = f"""\
# Invoker: v{metadata.version('invoker')}
# DO NOT MANUALLY EDIT THIS FILE.
#
# This script was generated with invoker.
# To regenerate file, run `invoker rebuild`.
# Date:\t{date.today().strftime("%Y-%m-%d")}
"""


def copy_resource(src_fn, dst_path, sign=False, preprocess_fn=lambda l: l):
    resource_files = _get_resources_path()
    with (resource_files / src_fn).open('rb') as f:
        file_hash = _compute_hash(f.read())
    with (resource_files / src_fn).open('r', encoding='utf-8') as inf, open(dst_path, "w") as outf:
        if sign:
            outf.write(GENERATED_MESSAGE)
            outf.write(f"# Hash:\t{file_hash}\n")
        for line in inf:
            outf.write(preprocess_fn(line))


def to_camel_case(string):
    return "".join([token.capitalize() for token in string.split("_")])

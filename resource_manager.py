from datetime import date
from importlib import metadata
from pathlib import Path
import hashlib
import os
from util import raise_error


class ResourceManager:
    """
    Handles resource hashing, file header signing, path resolution under the
    package `resources/` directory, and copying resources into a target project.
    """

    # Header injected when signing generated files
    GENERATED_MESSAGE = f"""\
# Invoker: v{metadata.version('invoker')}
# DO NOT MANUALLY EDIT THIS FILE.
#
# This script was generated with invoker.
# To regenerate file, run `invoker rebuild`.
"""

    @staticmethod
    def _compute_hash(raw_bytes: bytes) -> str:
        hasher = hashlib.md5()
        hasher.update(raw_bytes)
        return hasher.hexdigest()

    @staticmethod
    def _get_resources_path() -> Path:
        # This file lives under the package root; resources are sibling dir
        return Path(__file__).parent / "resources"

    @classmethod
    def _resolve_resource_path(cls, rel_path: str) -> Path:
        resources_root = cls._get_resources_path().resolve()
        rel = Path(rel_path)
        if rel.is_absolute():
            raise_error("Absolute resource paths are not allowed.")
        candidate = (resources_root / rel).resolve()
        # Ensure candidate remains under resources directory using pathlib
        try:
            candidate.relative_to(resources_root)
        except ValueError:
            raise_error("Resource path must be within the resources directory.")
        return candidate

    @classmethod
    def compute_resource_hash(cls, resource_rel_path: str) -> str:
        resource_path = cls._resolve_resource_path(resource_rel_path)
        with resource_path.open("rb") as f:
            return cls._compute_hash(f.read())

    @classmethod
    def compute_file_hash(cls, path: Path) -> tuple[str, str]:
        with open(path, "r") as f:
            while True:
                hash_line = f.readline()
                if not hash_line:
                    raise_error("Missing '# Hash:' header in signed file.")
                if hash_line.startswith("# Hash:"):
                    break
            stored_hash = hash_line.strip().split("\t")[1]
            computed_hash = cls._compute_hash(f.read().encode("ascii"))
        return stored_hash, computed_hash

    @classmethod
    def copy_resource(
        cls,
        src_rel_path: str,
        dst_path: Path,
        sign: bool = False,
        preprocess_fn=lambda l: l,
    ):
        resource_path = cls._resolve_resource_path(src_rel_path)
        with resource_path.open("rb") as f:
            file_hash = cls._compute_hash(f.read())
        with resource_path.open("r", encoding="utf-8") as inf, open(dst_path, "w") as outf:
            if sign:
                outf.write(cls.GENERATED_MESSAGE)
                outf.write(f"# Invoker resource: {src_rel_path}\n")
                outf.write(f"# Date: {date.today().strftime('%Y-%m-%d')}\n")
                outf.write(f"# Hash:\t{file_hash}\n")
            for line in inf:
                outf.write(preprocess_fn(line))



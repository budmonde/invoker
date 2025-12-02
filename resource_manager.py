from datetime import date
from importlib import metadata
from pathlib import Path
import hashlib
import os
from util import raise_error, warn


class ResourceManager:
    """
    Handles resource hashing, file header signing, path resolution under the
    package `resources/` directory, and copying resources into a target project.
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

    # Header injected when signing generated files
    GENERATED_MESSAGE = f"""\
# Invoker: v{metadata.version('invoker')}
# DO NOT MANUALLY EDIT THIS FILE.
#
# This script was generated with invoker.
# To regenerate file, run `invoker rebuild`.
"""

    @classmethod
    def add_invoker_header(cls, src_rel_path: str):
        """
        Build the invoker header lines for a given resource path.
        Computes the resource file hash internally.
        Returns a list of strings (each ending with newline) for callers to write.
        """
        resource_path = cls._resolve_resource_path(src_rel_path)
        with resource_path.open("rb") as f:
            file_hash = cls._compute_hash(f.read())
        header_lines = []
        header_lines.append(cls.GENERATED_MESSAGE)
        header_lines.append(f"# Invoker resource: {src_rel_path}\n")
        header_lines.append(f"# Date: {date.today().strftime('%Y-%m-%d')}\n")
        header_lines.append(f"# Hash:\t{file_hash}\n")
        return header_lines

    @classmethod
    def strip_invoker_header(cls, lines):
        """
        Remove invoker-generated header (including hash line and trailing blanks)
        from the top of a file, if present. Returns a new list of lines.
        """
        if not lines:
            return lines
        if not lines[0].startswith("# Invoker: v"):
            return lines
        end_idx = None
        for i, line in enumerate(lines[:50]):
            if line.startswith("# Hash:"):
                end_idx = i + 1
                break
        if end_idx is None:
            for i, line in enumerate(lines):
                if not line.startswith("#") and len(line.strip()) > 0:
                    end_idx = i
                    break
        if end_idx is None:
            return lines
        while end_idx < len(lines) and lines[end_idx].strip() == "":
            end_idx += 1
        return lines[end_idx:]

    @classmethod
    def compute_resource_hash(cls, resource_rel_path: str) -> str:
        resource_path = cls._resolve_resource_path(resource_rel_path)
        try:
            with resource_path.open("rb") as f:
                return cls._compute_hash(f.read())
        except FileNotFoundError:
            raise_error(f"Resource not found: {resource_rel_path}")

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
    def extract_resource_path_from_file(cls, path: Path) -> str | None:
        """
        Parse the generated file header to extract the resource relative path, if present.
        Returns the resource path string or None if not found.
        """
        try:
            with open(path, "r") as f:
                for _ in range(20):
                    line = f.readline()
                    if not line:
                        break
                    if line.startswith("# Invoker resource: "):
                        return line.split(": ", 1)[1].strip()
            return None
        except FileNotFoundError:
            return None

    @classmethod
    def import_resource(
        cls,
        src_rel_path: str,
        dst_path: Path,
        sign: bool = False,
        preprocess_fn=lambda l: l,
    ):
        resource_path = cls._resolve_resource_path(src_rel_path)
        with resource_path.open("r", encoding="utf-8") as inf, open(dst_path, "w") as outf:
            if sign:
                header_lines = cls.add_invoker_header(src_rel_path)
                outf.writelines(header_lines)
            for line in inf:
                outf.write(preprocess_fn(line))

    @classmethod
    def export_resource(cls, src_path: Path, dest_rel_path: str):
        """
        Copy a project-local file into the package resources directory,
        stripping any invoker-generated header if present.
        """
        dest = cls._get_resources_path() / dest_rel_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            warn(f"Overwriting existing resource at {dest}")

        with open(src_path, "r", encoding="utf-8") as inf, open(dest, "w", encoding="utf-8") as outf:
            lines = inf.readlines()
            cleaned = cls.strip_invoker_header(lines)
            outf.writelines(cleaned)



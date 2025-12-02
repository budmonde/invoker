from datetime import date
from importlib import metadata
from pathlib import Path
import hashlib
import os
import re
from util import raise_error, warn


class ResourceManager:
    """
    Handles resource hashing, file header signing, path resolution under the
    package `resources/` directory, and copying resources into a target project.
    """

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

    @staticmethod
    def _get_header_template_path() -> Path:
        return ResourceManager._get_resources_path() / "_header.txt"

    @classmethod
    def build_invoker_header(cls, src_rel_path: str):
        """
        Build the invoker header lines for a given resource path.
        Computes the resource file hash internally.
        Returns a list of strings (each ending with newline) for callers to write.
        """
        resource_path = cls._resolve_resource_path(src_rel_path)
        with resource_path.open("rb") as f:
            file_hash = cls._compute_hash(f.read())
        template = cls._get_header_template_path().read_text(encoding="utf-8")
        formatted = template.format(
            version=metadata.version('invoker'),
            resource=src_rel_path,
            date=date.today().strftime('%Y-%m-%d'),
            hash=file_hash,
        )
        return [formatted]

    @classmethod
    def parse_invoker_header(cls, path: Path):
        """
        Parse the top of a file and determine if it contains an invoker header.
        The header is matched using a regex generated from the header template.
        If matched, returns (num_lines, fields) where:
          - num_lines is the number of lines occupied by the header template
          - fields is a dict with keys: version, date, hash
        Otherwise returns (0, {}).
        """
        template = cls._get_header_template_path().read_text(encoding="utf-8")
        # Build a regex from the template by escaping literal text
        # and replacing placeholders with capturing groups.
        pattern = re.escape(template)
        pattern = pattern.replace(re.escape("{version}"), r"(?P<version>\d+\.\d+\.\d+)")
        pattern = pattern.replace(re.escape("{resource}"), r"(?P<resource>[^\n]+)")
        pattern = pattern.replace(re.escape("{date}"), r"(?P<date>\d{4}-\d{2}-\d{2})")
        pattern = pattern.replace(re.escape("{hash}"), r"(?P<hash>[0-9a-f]{32})")
        # Match from start of file
        text = path.read_text(encoding="utf-8")
        m = re.match(pattern, text)
        if not m:
            return 0, {}
        header_num_lines = len(template.splitlines())
        return header_num_lines, {
            "version": m.group("version"),
            "resource": m.group("resource"),
            "date": m.group("date"),
            "hash": m.group("hash"),
        }

    @classmethod
    def strip_invoker_header(cls, path: Path):
        """
        Remove invoker-generated header (including resource line and trailing blanks)
        from the top of a file at 'path', if present. Returns a new list of lines.
        """
        text = path.read_text(encoding="utf-8")
        lines = text.splitlines(keepends=True)
        header_num_lines, _ = cls.parse_invoker_header(path)
        if header_num_lines == 0:
            return lines
        idx = header_num_lines
        # Skip any following blank lines
        while idx < len(lines) and lines[idx].strip() == "":
            idx += 1
        return lines[idx:]

    @staticmethod
    def _compute_hash(raw_bytes: bytes) -> str:
        hasher = hashlib.md5()
        hasher.update(raw_bytes)
        return hasher.hexdigest()

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
        header_num_lines, fields = cls.parse_invoker_header(path)
        if header_num_lines == 0:
            raise_error(f"Missing invoker header in file '{path}'.")
        stored_hash = fields["hash"]
        stripped_lines = cls.strip_invoker_header(path)
        computed_hash = cls._compute_hash("".join(stripped_lines).encode("ascii"))
        return stored_hash, computed_hash

    # extract_resource_path_from_file removed; use parse_invoker_header instead

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
                header_lines = cls.build_invoker_header(src_rel_path)
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

        header_num_lines, _ = cls.parse_invoker_header(src_path)
        if header_num_lines > 0:
            cls._export_existing_resource(src_path, dest)
        else:
            cls._export_new_resource(src_path, dest)

    @classmethod
    def _export_existing_resource(cls, src_path: Path, dest: Path):
        """
        Export logic for an existing invoker-generated file (has header).
        - If stored hash == computed hash: skip export (no manual edits).
        - Else: overwrite destination with stripped content.
        """
        stored_hash, computed_hash = cls.compute_file_hash(src_path)
        if stored_hash == computed_hash:
            warn(f"No changes detected in '{src_path}'. Skipping export.")
            return

        cleaned_lines = cls.strip_invoker_header(src_path)
        cleaned_text = "".join(cleaned_lines)
        if dest.exists():
            warn(f"Overwriting existing resource at {dest}")
        with open(dest, "w", encoding="utf-8") as outf:
            outf.write(cleaned_text)

    @classmethod
    def _export_new_resource(cls, src_path: Path, dest: Path):
        """
        Export logic for a new resource (no header present).
        Simply write the file content as-is to the destination.
        """
        text = src_path.read_text(encoding="utf-8")
        with open(dest, "w", encoding="utf-8") as outf:
            outf.write(text)



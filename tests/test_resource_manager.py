"""Integration tests for utility functions in resource_manager.py."""
import hashlib
from datetime import date
import pytest

from importlib import metadata

from resource_manager import ResourceManager
import os


class TestComputeHash:
    """Test suite for _compute_hash function."""
    
    def test_compute_hash_returns_md5_hex(self):
        """Test that _compute_hash returns MD5 hash in hexadecimal format."""
        test_string = b"Hello, World!"
        result = ResourceManager._compute_hash(test_string)
        
        # Verify it's a valid hex string
        assert isinstance(result, str), "Hash should be a string"
        assert len(result) == 32, "MD5 hash should be 32 characters"
        assert all(c in '0123456789abcdef' for c in result), \
            "Hash should only contain hexadecimal characters"
    
    def test_compute_hash_consistent(self):
        """Test that _compute_hash returns consistent results for same input."""
        test_string = b"Test data"
        hash1 = ResourceManager._compute_hash(test_string)
        hash2 = ResourceManager._compute_hash(test_string)
        
        assert hash1 == hash2, "Same input should produce same hash"
    
    def test_compute_hash_different_inputs(self):
        """Test that different inputs produce different hashes."""
        hash1 = ResourceManager._compute_hash(b"input1")
        hash2 = ResourceManager._compute_hash(b"input2")
        
        assert hash1 != hash2, "Different inputs should produce different hashes"
    
    def test_compute_hash_empty_string(self):
        """Test that _compute_hash handles empty strings."""
        result = ResourceManager._compute_hash(b"")
        
        assert isinstance(result, str), "Should return string for empty input"
        assert len(result) == 32, "Should return valid MD5 hash"
    
    def test_compute_hash_matches_hashlib(self):
        """Test that _compute_hash produces correct MD5 hash."""
        test_string = b"Verify MD5 correctness"
        result = ResourceManager._compute_hash(test_string)
        
        # Compare with direct hashlib calculation
        expected = hashlib.md5(test_string).hexdigest()
        assert result == expected, "Hash should match hashlib.md5 output"


class TestComputeResourceHash:
    """Test suite for compute_resource_hash function."""
    
    def test_compute_resource_hash_invoker(self):
        """Test computing hash of invoker.py."""
        result = ResourceManager.compute_resource_hash("invoker.py")
        
        assert isinstance(result, str), "Hash should be a string"
        assert len(result) == 32, "MD5 hash should be 32 characters"
    
    def test_compute_resource_hash_script(self):
        """Test computing hash of script.py."""
        result = ResourceManager.compute_resource_hash("script.py")
        
        assert isinstance(result, str), "Hash should be a string"
        assert len(result) == 32, "MD5 hash should be 32 characters"
    
    def test_compute_resource_hash_module_base(self):
        """Test computing hash of module_base.py."""
        result = ResourceManager.compute_resource_hash("module_base.py")
        
        assert isinstance(result, str), "Hash should be a string"
        assert len(result) == 32, "MD5 hash should be 32 characters"
    
    def test_compute_resource_hash_consistent(self):
        """Test that computing hash multiple times returns same result."""
        hash1 = ResourceManager.compute_resource_hash("invoker.py")
        hash2 = ResourceManager.compute_resource_hash("invoker.py")
        
        assert hash1 == hash2, "Should return consistent hash for same resource"
    
    def test_compute_resource_hash_different_resources(self):
        """Test that different resources have different hashes."""
        hash1 = ResourceManager.compute_resource_hash("invoker.py")
        hash2 = ResourceManager.compute_resource_hash("script.py")
        
        assert hash1 != hash2, "Different resources should have different hashes"
    
    def test_compute_resource_hash_file_based_path(self):
        """Test that compute_resource_hash uses file-based path resolution."""
        # This test verifies that resources are found using __file__ based path
        # which works reliably across all installation types
        result = ResourceManager.compute_resource_hash("invoker.py")
        
        assert isinstance(result, str), "Hash should be a string"
        assert len(result) == 32, "MD5 hash should be 32 characters"
        
        # Verify the path resolution works by checking _get_resources_path
        resources_path = ResourceManager._get_resources_path()
        assert (resources_path / "invoker.py").exists(), \
            "Resource file should be accessible via file-based path"


class TestComputeFileHash:
    """Test suite for compute_file_hash function."""
    
    def test_compute_file_hash_with_hash_header(self, temp_project_dir):
        """Test computing hash of a file with hash header."""
        # Create a test file with proper invoker header
        test_file = temp_project_dir / "test_file.py"
        test_content = "print('Hello, World!')"
        test_hash = ResourceManager._compute_hash(test_content.encode('ascii'))
        
        with open(test_file, "w") as f:
            header_template = ResourceManager._get_header_template_path().read_text(encoding="utf-8")
            header_text = header_template.format(
                version=metadata.version('invoker'),
                resource="util/test_file.py",
                date=date.today().strftime("%Y-%m-%d"),
                hash=test_hash,
            )
            f.write(header_text + test_content)
        
        # Compute hash
        stored_hash, computed_hash = ResourceManager.compute_file_hash(test_file)
        
        assert stored_hash == test_hash, "Should extract stored hash correctly"
        assert computed_hash == test_hash, "Should compute hash correctly"
        assert stored_hash == computed_hash, "Stored and computed hashes should match"
    
    def test_compute_file_hash_modified_content(self, temp_project_dir):
        """Test that modified content produces different computed hash."""
        # Create a test file with proper invoker header
        test_file = temp_project_dir / "test_file.py"
        original_content = "print('Hello')"
        original_hash = ResourceManager._compute_hash(original_content.encode('ascii'))
        
        with open(test_file, "w") as f:
            header_template = ResourceManager._get_header_template_path().read_text(encoding="utf-8")
            header_text = header_template.format(
                version=metadata.version('invoker'),
                resource="util/test_file.py",
                date=date.today().strftime("%Y-%m-%d"),
                hash=original_hash,
            )
            f.write(header_text + "print('Modified content')")
        
        # Compute hash
        stored_hash, computed_hash = ResourceManager.compute_file_hash(test_file)
        
        assert stored_hash == original_hash, "Should extract original stored hash"
        assert computed_hash != stored_hash, "Computed hash should differ from stored hash"
    
    def test_compute_file_hash_multiline_content(self, temp_project_dir):
        """Test computing hash of multiline file."""
        test_file = temp_project_dir / "multiline.py"
        content = "line1\nline2\nline3\n"
        content_hash = ResourceManager._compute_hash(content.encode('ascii'))
        
        with open(test_file, "w") as f:
            header_template = ResourceManager._get_header_template_path().read_text(encoding="utf-8")
            header_text = header_template.format(
                version=metadata.version('invoker'),
                resource="util/multiline.py",
                date=date.today().strftime("%Y-%m-%d"),
                hash=content_hash,
            )
            f.write(header_text + content)
        
        stored_hash, computed_hash = ResourceManager.compute_file_hash(test_file)
        
        assert stored_hash == computed_hash, "Hashes should match for multiline content"

    def test_compute_file_hash_no_header_raises(self, temp_project_dir):
        """Calling compute_file_hash on a file without header should raise."""
        test_file = temp_project_dir / "no_header.py"
        test_file.write_text("print('no header here')\n", encoding="utf-8")
        with pytest.raises(SystemExit) as exc_info:
            ResourceManager.compute_file_hash(test_file)
        assert exc_info.value.code == 1


class TestCopyResource:
    """Test suite for copy_resource function."""
    
    def test_copy_resource_basic(self, temp_project_dir):
        """Test basic resource copying without signing."""
        dest_file = temp_project_dir / "copied_script.py"
        ResourceManager.import_resource("script.py", dest_file, sign=False)
        
        assert dest_file.exists(), "Destination file should be created"
        
        # Verify content was copied
        with open(dest_file, "r") as f:
            content = f.read()
        
        assert len(content) > 0, "File should have content"
        assert "from invoker import InvokerScript" in content, \
            "Should contain script template content"
    
    def test_copy_resource_with_signing(self, temp_project_dir):
        """Test resource copying with signing."""
        dest_file = temp_project_dir / "signed_file.py"
        ResourceManager.import_resource("invoker.py", dest_file, sign=True)
        
        assert dest_file.exists(), "Destination file should be created"
        
        # Read content
        with open(dest_file, "r") as f:
            lines = f.readlines()
        
        # Check signature components
        assert lines[0].startswith("# Invoker: v"), \
            "First line should have version header"
        assert "# DO NOT MANUALLY EDIT THIS FILE." in lines[1], \
            "Should have DO NOT EDIT warning"
        # Resource path and date lines
        assert any(line.startswith("# Resource name: invoker.py") for line in lines[:10]), \
            "Header should contain invoker resource path"
        assert any(line.startswith("# Date: ") for line in lines[:10]), \
            "Header should contain date line"

    def test_copy_resource_header_matches_resource_and_date(self, temp_project_dir):
        """Header should include exact resource path and today's date."""
        resource_rel_path = "util/image.py"
        dest_file = temp_project_dir / "signed_image_util.py"
        ResourceManager.import_resource(resource_rel_path, dest_file, sign=True)

        with open(dest_file, "r") as f:
            lines = f.readlines()

        expected_resource_line = f"# Resource name: {resource_rel_path}\n"
        expected_date_line = f"# Date: {date.today().strftime('%Y-%m-%d')}\n"

        assert expected_resource_line in lines[:10], \
            "Header should contain exact invoker resource path for copied file"
        assert expected_date_line in lines[:10], \
            "Header should contain today's date in YYYY-MM-DD format"
        
        # Find hash line
        hash_found = False
        for line in lines[:10]:
            if line.startswith("# Hash:"):
                hash_found = True
                break
        assert hash_found, "Should have hash line in header"
    
    def test_copy_resource_signed_hash_integrity(self, temp_project_dir):
        """Test that signed resource has correct hash."""
        dest_file = temp_project_dir / "hashed_file.py"
        ResourceManager.import_resource("module_base.py", dest_file, sign=True)
        
        # Compute resource hash
        resource_hash = ResourceManager.compute_resource_hash("module_base.py")
        
        # Compute file hash
        stored_hash, computed_hash = ResourceManager.compute_file_hash(dest_file)
        
        assert stored_hash == resource_hash, \
            "Stored hash should match resource hash"
        assert computed_hash == resource_hash, \
            "Computed hash should match resource hash"
    
    def test_copy_resource_with_preprocessing(self, temp_project_dir):
        """Test resource copying with preprocessing function."""
        dest_file = temp_project_dir / "preprocessed.py"
        
        # Define preprocessing function to replace placeholder
        def replace_placeholder(line):
            return line.replace("__MODULE__", "TestModule")
        
        ResourceManager.import_resource(
            "module_base.py",
            dest_file,
            sign=False,
            preprocess_fn=replace_placeholder
        )
        
        # Read content
        with open(dest_file, "r") as f:
            content = f.read()
        
        assert "TestModule" in content, "Placeholder should be replaced"
        assert "__MODULE__" not in content, "Original placeholder should be gone"
        assert "BaseTestModule" in content, \
            "Should contain preprocessed class name"
    
    def test_copy_resource_version_in_header(self, temp_project_dir):
        """Test that signed resource has correct version in header."""
        dest_file = temp_project_dir / "versioned.py"
        ResourceManager.import_resource("invoker.py", dest_file, sign=True)
        
        with open(dest_file, "r") as f:
            first_line = f.readline()
        
        # Extract version from header
        current_version = metadata.version('invoker')
        assert f"v{current_version}" in first_line, \
            f"Header should contain current version {current_version}"
    
    def test_copy_resource_preserves_content(self, temp_project_dir):
        """Test that resource content is preserved during copy."""
        dest_file = temp_project_dir / "preserved.py"
        ResourceManager.import_resource("script.py", dest_file, sign=False)
        
        # Read both source and destination using the helper
        resource_files = ResourceManager._get_resources_path()
        with (resource_files / "script.py").open('r', encoding='utf-8') as f:
            original_content = f.read()
        
        with open(dest_file, "r") as f:
            copied_content = f.read()
        
        assert original_content == copied_content, \
            "Content should be preserved when not signing"
    
    def test_copy_resource_file_based_path(self, temp_project_dir):
        """Test that copy_resource uses file-based path resolution."""
        # This test verifies that resources are copied using __file__ based path
        # which works reliably across all installation types
        dest_file = temp_project_dir / "file_based_test.py"
        
        ResourceManager.import_resource("script.py", dest_file, sign=True)
        
        # Verify file was created
        assert dest_file.exists(), "File should be created using file-based path"
        
        # Verify content
        with open(dest_file, "r") as f:
            content = f.read()
        
        assert "from invoker import InvokerScript" in content, \
            "Should contain correct imports"
        assert "# Hash:" in content, "Should contain hash when signed"
        
        # Verify the resources path exists
        resources_path = ResourceManager._get_resources_path()
        assert (resources_path / "script.py").exists(), \
            "Resource file should be accessible"


class TestInvokerHeaderOps:
    """Test suite for header build/parse/strip operations."""

    def test_build_invoker_header_contains_core_fields(self, tmp_path):
        header_lines = ResourceManager.build_invoker_header("script.py")
        header_text = "".join(header_lines)
        assert "# Invoker: v" in header_text, "Header should contain version line"
        assert "# DO NOT MANUALLY EDIT THIS FILE." in header_text, "Header should contain warning"
        assert "# Resource name: script.py" in header_text, "Header should contain resource path"
        assert "# Date: " in header_text, "Header should contain date line"
        assert "# Hash:" in header_text, "Header should contain hash line"

    def test_parse_invoker_header_extracts_fields(self, tmp_path):
        # Build header for existing resource and write to a temp file with a body
        header_text = "".join(ResourceManager.build_invoker_header("script.py"))
        body = "print('body')\n"
        temp_file = tmp_path / "with_header.py"
        temp_file.write_text(header_text + body, encoding="utf-8")

        num_lines, fields = ResourceManager.parse_invoker_header(temp_file)
        assert num_lines > 0, "Header line count should be positive when header present"
        assert fields.get("version") == metadata.version('invoker'), "Version should match package version"
        assert fields.get("resource") == "script.py", "Resource should be extracted from header"
        assert fields.get("date"), "Date should be present"
        assert fields.get("hash") and len(fields["hash"]) == 32, "Hash should be present and 32 hex chars"

    def test_strip_invoker_header_removes_header(self, tmp_path):
        header_text = "".join(ResourceManager.build_invoker_header("script.py"))
        body_lines = ["x = 1\n", "print(x)\n"]
        temp_file = tmp_path / "to_strip.py"
        temp_file.write_text(header_text + "".join(body_lines), encoding="utf-8")

        stripped = ResourceManager.strip_invoker_header(temp_file)
        assert stripped == body_lines, "strip_invoker_header should return only body lines"

    def test_strip_invoker_header_no_header_returns_same(self, tmp_path):
        body_lines = ["a = 10\n", "b = a + 1\n", "print(b)\n"]
        temp_file = tmp_path / "no_header.py"
        temp_file.write_text("".join(body_lines), encoding="utf-8")

        stripped = ResourceManager.strip_invoker_header(temp_file)
        assert stripped == body_lines, "Files without header should be returned unchanged"

    def test_strip_invoker_header_skips_trailing_blank_lines(self, tmp_path):
        header_text = "".join(ResourceManager.build_invoker_header("script.py"))
        # Add several blank lines after the header before the body
        blanks = ["\n", "\n", "\n"]
        body_lines = ["val = 99\n", "print(val)\n"]
        temp_file = tmp_path / "with_blanks.py"
        temp_file.write_text(header_text + "".join(blanks) + "".join(body_lines), encoding="utf-8")

        stripped = ResourceManager.strip_invoker_header(temp_file)
        assert stripped == body_lines, "Trailing blank lines after header should be skipped"


class TestResolveResourcePath:
    """Test suite for resource path resolution."""

    def test_resolve_valid_top_level_resource(self):
        p = ResourceManager._resolve_resource_path("invoker.py")
        assert p.name == "invoker.py"
        assert p.exists(), "Resolved top-level resource should exist"

    def test_resolve_valid_subpath_resource(self):
        p = ResourceManager._resolve_resource_path("util/image.py")
        assert p.name == "image.py"
        assert p.parent.name == "util"
        assert p.exists(), "Resolved subpath resource should exist"

    def test_resolve_absolute_path_raises(self):
        abs_path = os.path.abspath(__file__)
        import pytest
        with pytest.raises(SystemExit) as exc_info:
            ResourceManager._resolve_resource_path(abs_path)
        assert exc_info.value.code == 1

    def test_resolve_traversal_outside_raises(self):
        import pytest
        with pytest.raises(SystemExit) as exc_info:
            ResourceManager._resolve_resource_path("../outside.py")
        assert exc_info.value.code == 1


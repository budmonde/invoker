"""Integration tests for utility functions in util.py."""
from util import to_camel_case
import util
import pytest


class TestToCamelCase:
    """Test suite for to_camel_case function."""
    
    def test_to_camel_case_single_word(self):
        """Test converting single word to CamelCase."""
        assert to_camel_case("test") == "Test"
        assert to_camel_case("module") == "Module"
        assert to_camel_case("script") == "Script"
    
    def test_to_camel_case_two_words(self):
        """Test converting two words to CamelCase."""
        assert to_camel_case("my_module") == "MyModule"
        assert to_camel_case("test_script") == "TestScript"
        assert to_camel_case("base_class") == "BaseClass"
    
    def test_to_camel_case_multiple_words(self):
        """Test converting multiple words to CamelCase."""
        assert to_camel_case("my_test_module") == "MyTestModule"
        assert to_camel_case("a_b_c_d") == "ABCD"
        assert to_camel_case("very_long_module_name") == "VeryLongModuleName"
    
    def test_to_camel_case_already_capitalized(self):
        """Test converting already capitalized words."""
        assert to_camel_case("Test") == "Test"
        assert to_camel_case("MY_MODULE") == "MyModule"
    
    def test_to_camel_case_mixed_case(self):
        """Test converting mixed case words."""
        assert to_camel_case("myModule") == "Mymodule"
        assert to_camel_case("TestScript") == "Testscript"
    
    def test_to_camel_case_with_numbers(self):
        """Test converting words with numbers."""
        assert to_camel_case("module_v2") == "ModuleV2"
        assert to_camel_case("test_123") == "Test123"
        assert to_camel_case("v1_module") == "V1Module"
    
    def test_to_camel_case_empty_string(self):
        """Test converting empty string."""
        assert to_camel_case("") == ""
    
    def test_to_camel_case_no_underscores(self):
        """Test converting string without underscores."""
        assert to_camel_case("nounderscores") == "Nounderscores"
    
    def test_to_camel_case_consecutive_underscores(self):
        """Test converting string with consecutive underscores."""
        # Consecutive underscores create empty tokens
        assert to_camel_case("my__module") == "MyModule"
        assert to_camel_case("test___script") == "TestScript"
    
    def test_to_camel_case_real_examples(self):
        """Test with real-world examples from invoker usage."""
        # Examples from actual usage
        assert to_camel_case("my_test_script") == "MyTestScript"
        assert to_camel_case("data_processor") == "DataProcessor"
        assert to_camel_case("neural_network_model") == "NeuralNetworkModel"
        assert to_camel_case("image_augmentation") == "ImageAugmentation"


class TestIsEditableInstall:
    """Test suite for is_editable_install heuristic."""

    def test_is_editable_install_true_for_dev_paths(self, monkeypatch):
        # Simulate repository-style path (no site-packages/dist-packages in parents)
        fake_util_path = "/home/user/dev/invoker/util.py"
        monkeypatch.setattr(util, "__file__", fake_util_path, raising=False)
        assert util.is_editable_install() is True

    def test_is_editable_install_false_for_site_packages(self, monkeypatch):
        # Simulate installed package path under site-packages
        fake_util_path = "/usr/lib/python3.11/site-packages/invoker/util.py"
        monkeypatch.setattr(util, "__file__", fake_util_path, raising=False)
        assert util.is_editable_install() is False
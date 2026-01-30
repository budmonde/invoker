"""Integration tests for utility functions in util.py."""

import util
from util import InheritanceAnalyzer, to_camel_case


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


class TestInheritanceAnalyzer:
    """Test suite for AST-based inheritance analysis."""

    def test_direct_inheritance(self):
        """Test detection of direct InvokerModule inheritance."""
        content = """
from invoker import InvokerModule

class MyModule(InvokerModule):
    pass
"""
        analyzer = InheritanceAnalyzer(content)
        assert analyzer.has_subclass_of("invoker", "InvokerModule") is True

    def test_transitive_inheritance(self):
        """Test detection of transitive inheritance (Foo -> Bar -> InvokerModule)."""
        content = """
from invoker import InvokerModule

class BaseLoader(InvokerModule):
    pass

class CsvLoader(BaseLoader):
    pass
"""
        analyzer = InheritanceAnalyzer(content)
        assert analyzer.has_subclass_of("invoker", "InvokerModule") is True

    def test_deep_transitive_inheritance(self):
        """Test detection of deep inheritance chain (A -> B -> C -> InvokerModule)."""
        content = """
from invoker import InvokerModule

class Base(InvokerModule):
    pass

class Middle(Base):
    pass

class Leaf(Middle):
    pass
"""
        analyzer = InheritanceAnalyzer(content)
        assert analyzer.has_subclass_of("invoker", "InvokerModule") is True

    def test_multiple_inheritance_with_invoker_module(self):
        """Test detection with multiple inheritance including InvokerModule."""
        content = """
from invoker import InvokerModule

class Mixin:
    pass

class MyModule(Mixin, InvokerModule):
    pass
"""
        analyzer = InheritanceAnalyzer(content)
        assert analyzer.has_subclass_of("invoker", "InvokerModule") is True

    def test_transitive_multiple_inheritance(self):
        """Test transitive inheritance through multiple inheritance."""
        content = """
from invoker import InvokerModule

class Base(InvokerModule):
    pass

class Mixin:
    pass

class Child(Mixin, Base):
    pass
"""
        analyzer = InheritanceAnalyzer(content)
        assert analyzer.has_subclass_of("invoker", "InvokerModule") is True

    def test_aliased_import(self):
        """Test detection when InvokerModule is imported with alias."""
        content = """
from invoker import InvokerModule as IM

class MyModule(IM):
    pass
"""
        analyzer = InheritanceAnalyzer(content)
        assert analyzer.has_subclass_of("invoker", "InvokerModule") is True

    def test_no_invoker_import(self):
        """Test file without invoker import returns False."""
        content = """
class SomeClass:
    pass

class AnotherClass(SomeClass):
    pass
"""
        analyzer = InheritanceAnalyzer(content)
        assert analyzer.has_subclass_of("invoker", "InvokerModule") is False

    def test_invoker_import_but_no_subclass(self):
        """Test file that imports InvokerModule but doesn't subclass it."""
        content = """
from invoker import InvokerModule

class UnrelatedClass:
    pass
"""
        analyzer = InheritanceAnalyzer(content)
        assert analyzer.has_subclass_of("invoker", "InvokerModule") is False

    def test_class_with_unrelated_base(self):
        """Test file with class inheriting from unrelated base."""
        content = """
from invoker import InvokerModule

class SomeBase:
    pass

class Child(SomeBase):
    pass
"""
        analyzer = InheritanceAnalyzer(content)
        assert analyzer.has_subclass_of("invoker", "InvokerModule") is False

    def test_syntax_error_returns_false(self):
        """Test that syntax errors return False gracefully."""
        content = """
this is not valid python syntax
class Broken(
"""
        analyzer = InheritanceAnalyzer(content)
        assert analyzer.has_subclass_of("invoker", "InvokerModule") is False

    def test_empty_file(self):
        """Test empty file returns False."""
        content = ""
        analyzer = InheritanceAnalyzer(content)
        assert analyzer.has_subclass_of("invoker", "InvokerModule") is False

    def test_only_imports(self):
        """Test file with only imports returns False."""
        content = """
from invoker import InvokerModule
import os
"""
        analyzer = InheritanceAnalyzer(content)
        assert analyzer.has_subclass_of("invoker", "InvokerModule") is False

    def test_circular_inheritance_handled(self):
        """Test that circular inheritance doesn't cause infinite loop."""
        # This is invalid Python but should be handled gracefully
        content = """
from invoker import InvokerModule

class A(B):
    pass

class B(A):
    pass
"""
        analyzer = InheritanceAnalyzer(content)
        # Should return False (no path to InvokerModule) without hanging
        assert analyzer.has_subclass_of("invoker", "InvokerModule") is False

    def test_get_imports_from(self):
        """Test getting imports from a specific module."""
        content = """
from invoker import InvokerModule, InvokerScript
from os import path
"""
        analyzer = InheritanceAnalyzer(content)
        imports = analyzer.get_imports_from("invoker")
        assert "InvokerModule" in imports
        assert "InvokerScript" in imports
        assert len(imports) == 2

    def test_get_imports_from_with_alias(self):
        """Test getting imports with aliases."""
        content = """
from invoker import InvokerModule as IM
"""
        analyzer = InheritanceAnalyzer(content)
        imports = analyzer.get_imports_from("invoker")
        assert "IM" in imports
        assert "InvokerModule" not in imports

    def test_get_class_bases(self):
        """Test getting base classes of a class."""
        content = """
class Parent:
    pass

class Child(Parent):
    pass

class Multi(Parent, object):
    pass
"""
        analyzer = InheritanceAnalyzer(content)
        assert analyzer.get_class_bases("Parent") == []
        assert analyzer.get_class_bases("Child") == ["Parent"]
        assert analyzer.get_class_bases("Multi") == ["Parent", "object"]
        assert analyzer.get_class_bases("NonExistent") == []

    def test_get_all_classes(self):
        """Test getting all class names."""
        content = """
class A:
    pass

class B(A):
    pass

class C:
    pass
"""
        analyzer = InheritanceAnalyzer(content)
        classes = analyzer.get_all_classes()
        assert set(classes) == {"A", "B", "C"}

    def test_inherits_from_direct(self):
        """Test direct inheritance check."""
        content = """
class Parent:
    pass

class Child(Parent):
    pass
"""
        analyzer = InheritanceAnalyzer(content)
        assert analyzer.inherits_from("Child", {"Parent"}) is True
        assert analyzer.inherits_from("Parent", {"Parent"}) is True
        assert analyzer.inherits_from("Child", {"Other"}) is False

    def test_inherits_from_transitive(self):
        """Test transitive inheritance check."""
        content = """
class A:
    pass

class B(A):
    pass

class C(B):
    pass
"""
        analyzer = InheritanceAnalyzer(content)
        assert analyzer.inherits_from("C", {"A"}) is True
        assert analyzer.inherits_from("B", {"A"}) is True
        assert analyzer.inherits_from("A", {"A"}) is True

    def test_different_module_inheritance(self):
        """Test inheritance detection for different module/class combos."""
        content = """
from other_module import OtherBase

class MyClass(OtherBase):
    pass
"""
        analyzer = InheritanceAnalyzer(content)
        assert analyzer.has_subclass_of("other_module", "OtherBase") is True
        assert analyzer.has_subclass_of("invoker", "InvokerModule") is False

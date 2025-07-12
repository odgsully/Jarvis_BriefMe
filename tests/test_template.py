"""Tests for template engine."""
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from src.template_engine import TemplateEngine


class TestTemplateEngine:
    """Test template engine functionality."""
    
    @pytest.fixture
    def temp_template_dir(self):
        """Create a temporary template directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)
    
    @pytest.fixture
    def template_engine(self, temp_template_dir):
        """Create template engine with temporary directory."""
        with patch('src.template_engine.settings') as mock_settings:
            mock_settings.templates_dir = temp_template_dir
            return TemplateEngine()
    
    def test_rotate_phrase_deterministic(self, template_engine):
        """Test phrase rotation with seed is deterministic."""
        phrases = ["phrase1", "phrase2", "phrase3"]
        
        # Same seed should produce same result
        result1 = template_engine._rotate_phrase(phrases, seed="test_seed")
        result2 = template_engine._rotate_phrase(phrases, seed="test_seed")
        assert result1 == result2
        
        # Different seed should (likely) produce different result
        result3 = template_engine._rotate_phrase(phrases, seed="different_seed")
        # Note: There's a chance they could be the same, but unlikely with 3 choices
    
    def test_rotate_phrase_empty_list(self, template_engine):
        """Test rotation with empty phrase list."""
        result = template_engine._rotate_phrase([], seed="test")
        assert result == ""
    
    def test_render_template(self, temp_template_dir, template_engine):
        """Test template rendering."""
        # Create a test template
        template_content = """Hello {{ name }}!
Today is {{ date }}.
Let's {{ GET_TO_IT_SAYING }} the work."""
        
        template_path = temp_template_dir / "test_template.txt"
        template_path.write_text(template_content)
        
        # Render template
        context = {
            "name": "Garrett",
            "date": "Wednesday",
        }
        
        result = template_engine.render_template("test_template.txt", context)
        
        assert "Hello Garrett!" in result
        assert "Today is Wednesday." in result
        assert "Let's" in result
        assert "the work." in result
        # GET_TO_IT_SAYING should be auto-populated
        assert any(phrase in result for phrase in template_engine.get_to_it_phrases)
    
    def test_get_template_variables(self, temp_template_dir, template_engine):
        """Test extracting variables from template."""
        # Create a test template
        template_content = """{{ var1 }} and {{ var2 }}
{% if condition %}{{ var3 }}{% endif %}
{{ var1 }} again"""
        
        template_path = temp_template_dir / "test_template.txt"
        template_path.write_text(template_content)
        
        variables = template_engine.get_template_variables("test_template.txt")
        
        # Should find unique variables
        assert "var1" in variables
        assert "var2" in variables
        assert "var3" in variables
        assert len(set(variables)) == len(variables)  # No duplicates
    
    def test_validate_context(self, temp_template_dir, template_engine):
        """Test context validation."""
        # Create a test template
        template_content = "{{ required1 }} and {{ required2 }}"
        
        template_path = temp_template_dir / "test_template.txt"
        template_path.write_text(template_content)
        
        # Test with complete context
        complete_context = {
            "required1": "value1",
            "required2": "value2",
        }
        missing = template_engine.validate_context("test_template.txt", complete_context)
        assert len(missing) == 0
        
        # Test with incomplete context
        incomplete_context = {
            "required1": "value1",
        }
        missing = template_engine.validate_context("test_template.txt", incomplete_context)
        assert "required2" in missing
        assert len(missing) == 1
    
    def test_render_template_error_handling(self, template_engine):
        """Test error handling in template rendering."""
        # Try to render non-existent template
        with pytest.raises(Exception):
            template_engine.render_template("non_existent.txt", {})
    
    def test_custom_filters(self, temp_template_dir, template_engine):
        """Test custom filters are available."""
        # Create a template using custom filter
        template_content = "{{ phrases|rotate_phrase }}"
        
        template_path = temp_template_dir / "test_template.txt"
        template_path.write_text(template_content)
        
        context = {
            "phrases": ["option1", "option2", "option3"]
        }
        
        result = template_engine.render_template("test_template.txt", context)
        
        # Should be one of the options
        assert result.strip() in ["option1", "option2", "option3"]
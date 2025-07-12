"""Tests for content generators."""
import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.generators.codebase import CodebaseSelector, Repository
from src.generators.summariser import Summarizer


class TestCodebaseSelector:
    """Test codebase selector functionality."""
    
    @pytest.fixture
    def temp_history_file(self):
        """Create a temporary history file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = Path(f.name)
        yield temp_path
        temp_path.unlink(missing_ok=True)
    
    @pytest.fixture
    def mock_settings(self, temp_history_file):
        """Mock settings with temporary paths."""
        with patch('src.generators.codebase.settings') as mock:
            mock.root_dir = temp_history_file.parent
            mock.github_token = "fake_token"
            yield mock
    
    def test_load_history_empty(self, mock_settings):
        """Test loading history when file doesn't exist."""
        selector = CodebaseSelector()
        history = selector._load_history()
        assert history == []
    
    def test_save_and_load_history(self, mock_settings):
        """Test saving and loading history."""
        selector = CodebaseSelector()
        
        # Save history
        test_history = ["repo1", "repo2", "repo3"]
        selector._save_history(test_history)
        
        # Load history
        loaded_history = selector._load_history()
        assert loaded_history == test_history
    
    def test_select_repository_no_repetition(self, mock_settings):
        """Test repository selection avoids recent repetitions."""
        selector = CodebaseSelector()
        
        # Create test repositories
        repos = [
            Repository(
                name=f"repo{i}",
                full_name=f"user/repo{i}",
                description=f"Description {i}",
                url=f"https://github.com/user/repo{i}",
                language="Python",
                stars=i * 10,
                created_at="2024-01-01",
                updated_at="2024-01-01",
                private=False,
                size=100,
                default_branch="main",
                topics=[]
            )
            for i in range(5)
        ]
        
        # Set history with recent selections
        selector._save_history(["repo1", "repo2"])
        
        # Select repository multiple times
        selected_names = set()
        for _ in range(10):
            selected = selector.select_repository(repos)
            selected_names.add(selected.name)
        
        # Should avoid repo1 and repo2 if possible
        assert "repo0" in selected_names or "repo3" in selected_names or "repo4" in selected_names
    
    def test_select_repository_single_repo(self, mock_settings):
        """Test selection when only one repository exists."""
        selector = CodebaseSelector()
        
        repo = Repository(
            name="only-repo",
            full_name="user/only-repo",
            description="The only repository",
            url="https://github.com/user/only-repo",
            language="Python",
            stars=100,
            created_at="2024-01-01",
            updated_at="2024-01-01",
            private=False,
            size=100,
            default_branch="main",
            topics=[]
        )
        
        selected = selector.select_repository([repo])
        assert selected.name == "only-repo"
    
    @pytest.mark.asyncio
    async def test_fetch_repo_structure(self, mock_settings):
        """Test fetching repository structure."""
        selector = CodebaseSelector()
        
        # Mock the HTTP response
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {"name": "src", "type": "dir"},
            {"name": "README.md", "type": "file"},
            {"name": "tests", "type": "dir"},
            {"name": "setup.py", "type": "file"},
        ]
        
        selector.client.get = AsyncMock(return_value=mock_response)
        
        repo = Repository(
            name="test-repo",
            full_name="user/test-repo",
            description="Test repository",
            url="https://github.com/user/test-repo",
            language="Python",
            stars=100,
            created_at="2024-01-01",
            updated_at="2024-01-01",
            private=False,
            size=100,
            default_branch="main",
            topics=[]
        )
        
        structure = await selector.fetch_repo_structure(repo)
        
        assert "Repository: test-repo" in structure
        assert "📁 src/" in structure
        assert "📁 tests/" in structure
        assert "📄 README.md" in structure
        assert "📄 setup.py" in structure


class TestSummarizer:
    """Test content summarizer."""
    
    @pytest.fixture
    def mock_openai_response(self):
        """Mock OpenAI API response."""
        mock_choice = MagicMock()
        mock_choice.message.content = "This is a test summary."
        
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        
        return mock_response
    
    @pytest.mark.asyncio
    async def test_summarize_success(self, mock_openai_response):
        """Test successful summarization."""
        summarizer = Summarizer()
        
        # Mock the OpenAI client
        summarizer.client.chat.completions.create = AsyncMock(
            return_value=mock_openai_response
        )
        
        result = await summarizer.summarize(
            "This is test content to summarize",
            "summary",
            100
        )
        
        assert result == "This is a test summary."
        
        # Check that the API was called
        summarizer.client.chat.completions.create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_summarize_empty_content(self):
        """Test summarizing empty content."""
        summarizer = Summarizer()
        
        result = await summarizer.summarize("", "summary", 100)
        assert result == "(No content to summarize)"
    
    @pytest.mark.asyncio
    async def test_summarize_error_handling(self):
        """Test error handling in summarization."""
        summarizer = Summarizer()
        
        # Mock the OpenAI client to raise an error
        summarizer.client.chat.completions.create = AsyncMock(
            side_effect=Exception("API Error")
        )
        
        result = await summarizer.summarize(
            "Test content",
            "summary",
            100
        )
        
        assert "(Summary generation failed:" in result
        assert "API Error" in result
    
    def test_build_prompt_types(self):
        """Test different prompt types."""
        summarizer = Summarizer()
        
        # Test summary prompt
        prompt = summarizer._build_prompt("test content", "summary", 100, None)
        assert "Summarize" in prompt
        assert "100 words" in prompt
        assert "test content" in prompt
        
        # Test keypoints prompt
        prompt = summarizer._build_prompt("test content", "keypoints", 50, None)
        assert "key facts" in prompt
        assert "50 words" in prompt
        
        # Test with additional context
        prompt = summarizer._build_prompt(
            "test content",
            "summary",
            100,
            "Additional context here"
        )
        assert "Additional context here" in prompt
    
    @pytest.mark.asyncio
    async def test_generate_fact(self, mock_openai_response):
        """Test fact generation."""
        summarizer = Summarizer()
        
        # Mock the OpenAI client
        summarizer.client.chat.completions.create = AsyncMock(
            return_value=mock_openai_response
        )
        
        result = await summarizer.generate_fact("World War 1", "ww1", 100)
        
        assert result == "This is a test summary."
        
        # Verify the call included WW1 prompt
        call_args = summarizer.client.chat.completions.create.call_args
        messages = call_args[1]['messages']
        assert any("World War 1" in msg['content'] for msg in messages)
    
    @pytest.mark.asyncio
    async def test_batch_summarize(self, mock_openai_response):
        """Test batch summarization."""
        summarizer = Summarizer()
        
        # Mock the OpenAI client
        summarizer.client.chat.completions.create = AsyncMock(
            return_value=mock_openai_response
        )
        
        items = [
            {"key": "item1", "content": "Content 1", "type": "summary"},
            {"key": "item2", "content": "Content 2", "type": "keypoints"},
        ]
        
        results = await summarizer.batch_summarize(items, 100)
        
        assert len(results) == 2
        assert results["item1"] == "This is a test summary."
        assert results["item2"] == "This is a test summary."
        
        # Verify multiple calls were made
        assert summarizer.client.chat.completions.create.call_count == 2
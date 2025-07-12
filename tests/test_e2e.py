"""End-to-end integration tests."""
import asyncio
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.main import BriefingOrchestrator


class TestE2E:
    """End-to-end integration tests."""
    
    @pytest.fixture
    def temp_output_dir(self):
        """Create temporary output directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir)
            dailies_dir = base_path / "dailies"
            tables_dir = base_path / "tables"
            templates_dir = base_path / "templates"
            datasets_dir = base_path / "datasets"
            
            # Create directories
            dailies_dir.mkdir(parents=True)
            tables_dir.mkdir(parents=True)
            templates_dir.mkdir(parents=True)
            datasets_dir.mkdir(parents=True)
            
            # Create minimal template
            template_content = """Daily Brief for {{ FULLDATE }}
Country: {{ COUNTRY_OF_THE_DAY }}
Article: {{ YC_ARTICLE_PICK }}
Cycle: Year {{ CURRENT_STUDY_YEAR }}, State {{ CURRENT_STUDY_STATE }}, Days {{ DAYS_LEFT }}"""
            
            template_path = templates_dir / "daily_template.txt"
            template_path.write_text(template_content)
            
            # Create minimal countries CSV
            countries_csv = """Country,Capital,Region,Subregion,Population,Area,Languages,Currencies,Latitude,Longitude
TestCountry,TestCapital,TestRegion,TestSubregion,1000000,10000,English,TestCurrency,0,0"""
            
            countries_path = datasets_dir / "Countries.csv"
            countries_path.write_text(countries_csv)
            
            # Create minimal dataset files
            oscars_csv = """Year,Best Picture,Best Actor,Best Cinematography,Best Score,Best Foreign Film
1980,Test Picture,Test Actor,Test Cinematography,Test Score,Test Foreign Film"""
            
            presidents_csv = """Year,President,Vice President,Major Decision
1980,Test President,Test VP,Test Decision"""
            
            inventions_csv = """Year,Invention,Summary
1980,Test Invention,Test Summary"""
            
            (datasets_dir / "Oscars.csv").write_text(oscars_csv)
            (datasets_dir / "Presidents.csv").write_text(presidents_csv)
            (datasets_dir / "Inventions.csv").write_text(inventions_csv)
            
            yield base_path
    
    @pytest.fixture
    def mock_settings(self, temp_output_dir):
        """Mock settings for testing."""
        with patch('src.main.settings') as mock_settings:
            mock_settings.root_dir = temp_output_dir
            mock_settings.outputs_dir = temp_output_dir
            mock_settings.dailies_dir = temp_output_dir / "dailies"
            mock_settings.tables_dir = temp_output_dir / "tables"
            mock_settings.templates_dir = temp_output_dir / "templates"
            mock_settings.datasets_dir = temp_output_dir / "datasets"
            mock_settings.ensure_directories = lambda: None
            mock_settings.openai_api_key = "test_key"
            mock_settings.notion_api_key = "test_notion_key"
            mock_settings.gmail_app_password = "test_password"
            mock_settings.gmail_from = "test@example.com"
            mock_settings.gmail_to = "recipient@example.com"
            mock_settings.github_token = "test_github_token"
            
            # Also patch in other modules
            with patch('src.file_writer.settings', mock_settings), \
                 patch('src.template_engine.settings', mock_settings), \
                 patch('src.emailer.settings', mock_settings), \
                 patch('src.generators.cycle.settings', mock_settings), \
                 patch('src.generators.codebase.settings', mock_settings), \
                 patch('src.generators.summariser.settings', mock_settings), \
                 patch('src.fetchers.countries.settings', mock_settings):
                yield mock_settings
    
    @pytest.mark.asyncio
    async def test_full_briefing_generation_dry_run(self, mock_settings, temp_output_dir):
        """Test complete briefing generation in dry-run mode."""
        
        # Mock external API calls
        with patch('src.fetchers.hn.HackerNewsFetcher') as mock_hn, \
             patch('src.fetchers.github_trend.GitHubTrendingFetcher') as mock_gh, \
             patch('src.fetchers.notion.NotionFetcher') as mock_notion, \
             patch('src.generators.codebase.CodebaseSelector') as mock_codebase, \
             patch('src.generators.summariser.Summarizer') as mock_summarizer:
            
            # Setup HN mock
            mock_hn_instance = AsyncMock()
            mock_article = MagicMock()
            mock_article.title = "Test HN Article"
            mock_hn_instance.get_top_article.return_value = (mock_article, ["test", "keywords"])
            mock_hn.return_value.__aenter__.return_value = mock_hn_instance
            
            # Setup GitHub mock
            mock_gh_instance = AsyncMock()
            mock_repo = MagicMock()
            mock_repo.full_name = "test/repo"
            mock_repo.description = "Test description"
            mock_gh_instance.get_top_mcp_repo.return_value = mock_repo
            mock_gh.return_value.__aenter__.return_value = mock_gh_instance
            
            # Setup Notion mock
            mock_notion_instance = AsyncMock()
            mock_notion_instance.fetch_transcripts_last_week.return_value = []
            mock_notion_instance.fetch_all_cs_terms.return_value = []
            mock_notion_instance.fetch_all_spanish_phrases.return_value = []
            mock_notion.return_value.__aenter__.return_value = mock_notion_instance
            
            # Setup Codebase mock
            mock_codebase_instance = AsyncMock()
            mock_codebase_instance.get_codebase_of_the_day.return_value = ("test-repo", "Test repo description")
            mock_codebase.return_value.__aenter__.return_value = mock_codebase_instance
            
            # Setup Summarizer mock
            mock_summarizer_instance = AsyncMock()
            mock_summarizer_instance.summarize.return_value = "Test summary"
            mock_summarizer_instance.generate_fact.return_value = "Test fact"
            mock_summarizer.return_value = mock_summarizer_instance
            
            # Create orchestrator and run
            orchestrator = BriefingOrchestrator()
            
            # Run the briefing generation
            success = await orchestrator.generate_briefing(dry_run=True, send_email=False)
            
            # Verify success
            assert success
            
            # Check that files were created
            dailies_dir = temp_output_dir / "dailies"
            tables_dir = temp_output_dir / "tables"
            
            # Should have one TXT file
            txt_files = list(dailies_dir.glob("Daily_*.txt"))
            assert len(txt_files) == 1
            
            # Should have one XLSX file
            xlsx_files = list(tables_dir.glob("Table_*.xlsx"))
            assert len(xlsx_files) == 1
            
            # Check TXT content
            txt_content = txt_files[0].read_text()
            assert "Daily Brief for" in txt_content
            assert "Country: TestCountry" in txt_content
            assert "Article: Test HN Article" in txt_content
            assert "Year 1980" in txt_content
            assert "State Alabama" in txt_content
            assert "Days 3" in txt_content
    
    @pytest.mark.asyncio
    async def test_error_handling_continues_execution(self, mock_settings, temp_output_dir):
        """Test that errors in individual components don't stop execution."""
        
        # Mock components to raise errors
        with patch('src.fetchers.hn.HackerNewsFetcher') as mock_hn, \
             patch('src.fetchers.github_trend.GitHubTrendingFetcher') as mock_gh, \
             patch('src.fetchers.notion.NotionFetcher') as mock_notion, \
             patch('src.generators.codebase.CodebaseSelector') as mock_codebase, \
             patch('src.generators.summariser.Summarizer') as mock_summarizer:
            
            # Setup mocks to raise errors
            mock_hn_instance = AsyncMock()
            mock_hn_instance.get_top_article.side_effect = Exception("HN Error")
            mock_hn.return_value.__aenter__.return_value = mock_hn_instance
            
            mock_gh_instance = AsyncMock()
            mock_gh_instance.get_top_mcp_repo.side_effect = Exception("GitHub Error")
            mock_gh.return_value.__aenter__.return_value = mock_gh_instance
            
            mock_notion_instance = AsyncMock()
            mock_notion_instance.fetch_transcripts_last_week.side_effect = Exception("Notion Error")
            mock_notion_instance.fetch_all_cs_terms.side_effect = Exception("Notion Error")
            mock_notion_instance.fetch_all_spanish_phrases.side_effect = Exception("Notion Error")
            mock_notion.return_value.__aenter__.return_value = mock_notion_instance
            
            mock_codebase_instance = AsyncMock()
            mock_codebase_instance.get_codebase_of_the_day.side_effect = Exception("Codebase Error")
            mock_codebase.return_value.__aenter__.return_value = mock_codebase_instance
            
            mock_summarizer_instance = AsyncMock()
            mock_summarizer_instance.summarize.side_effect = Exception("Summarizer Error")
            mock_summarizer_instance.generate_fact.side_effect = Exception("Fact Error")
            mock_summarizer.return_value = mock_summarizer_instance
            
            # Create orchestrator and run
            orchestrator = BriefingOrchestrator()
            
            # Run the briefing generation
            success = await orchestrator.generate_briefing(dry_run=True, send_email=False)
            
            # Should still succeed despite errors
            assert success
            
            # Check that files were still created
            dailies_dir = temp_output_dir / "dailies"
            tables_dir = temp_output_dir / "tables"
            
            txt_files = list(dailies_dir.glob("Daily_*.txt"))
            assert len(txt_files) == 1
            
            xlsx_files = list(tables_dir.glob("Table_*.xlsx"))
            assert len(xlsx_files) == 1
            
            # Check that error placeholders are in content
            txt_content = txt_files[0].read_text()
            assert "data unavailable" in txt_content or "not available" in txt_content
    
    @pytest.mark.asyncio 
    async def test_missing_fields_detection(self, mock_settings, temp_output_dir):
        """Test that missing fields are properly detected and reported."""
        
        # Mock all components to return empty/error data
        with patch('src.fetchers.hn.HackerNewsFetcher') as mock_hn, \
             patch('src.fetchers.github_trend.GitHubTrendingFetcher') as mock_gh, \
             patch('src.fetchers.notion.NotionFetcher') as mock_notion, \
             patch('src.generators.codebase.CodebaseSelector') as mock_codebase, \
             patch('src.generators.summariser.Summarizer') as mock_summarizer:
            
            # Setup all mocks to return None/empty
            mock_hn_instance = AsyncMock()
            mock_hn_instance.get_top_article.return_value = None
            mock_hn.return_value.__aenter__.return_value = mock_hn_instance
            
            mock_gh_instance = AsyncMock()
            mock_gh_instance.get_top_mcp_repo.return_value = None
            mock_gh.return_value.__aenter__.return_value = mock_gh_instance
            
            mock_notion_instance = AsyncMock()
            mock_notion_instance.fetch_transcripts_last_week.return_value = []
            mock_notion_instance.fetch_all_cs_terms.return_value = []
            mock_notion_instance.fetch_all_spanish_phrases.return_value = []
            mock_notion.return_value.__aenter__.return_value = mock_notion_instance
            
            mock_codebase_instance = AsyncMock()
            mock_codebase_instance.get_codebase_of_the_day.return_value = ("", "")
            mock_codebase.return_value.__aenter__.return_value = mock_codebase_instance
            
            mock_summarizer_instance = AsyncMock()
            mock_summarizer_instance.summarize.return_value = ""
            mock_summarizer_instance.generate_fact.return_value = ""
            mock_summarizer.return_value = mock_summarizer_instance
            
            # Create orchestrator and run
            orchestrator = BriefingOrchestrator()
            
            # Mock the emailer to capture missing fields
            with patch.object(orchestrator.emailer, 'send_daily_brief') as mock_send_brief, \
                 patch.object(orchestrator.emailer, 'send_alert_email') as mock_send_alert:
                
                mock_send_brief.return_value = True
                mock_send_alert.return_value = True
                
                # Run dry run
                success = await orchestrator.generate_briefing(dry_run=True, send_email=False)
                assert success
                
                # Check that missing fields were detected
                missing_fields = orchestrator.file_writer.get_missing_fields(
                    await orchestrator.gather_data()
                )
                
                # Should have many missing fields
                assert len(missing_fields) > 0
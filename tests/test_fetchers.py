"""Tests for data fetchers."""
import pytest
import respx
from httpx import Response

from src.fetchers.hn import HackerNewsFetcher, Article
from src.fetchers.github_trend import GitHubTrendingFetcher, TrendingRepo
from src.fetchers.countries import CountriesFetcher


class TestHackerNewsFetcher:
    """Test Hacker News fetcher."""
    
    @pytest.mark.asyncio
    @respx.mock
    async def test_fetch_top_stories(self):
        """Test fetching top story IDs."""
        # Mock the API response
        respx.get("https://hacker-news.firebaseio.com/v0/topstories.json").mock(
            return_value=Response(200, json=[1, 2, 3, 4, 5])
        )
        
        async with HackerNewsFetcher() as fetcher:
            story_ids = await fetcher.fetch_top_stories(limit=3)
            
        assert len(story_ids) == 3
        assert story_ids == [1, 2, 3]
    
    @pytest.mark.asyncio
    @respx.mock
    async def test_fetch_item(self):
        """Test fetching a specific item."""
        # Mock the API response
        item_data = {
            "id": 1,
            "type": "story",
            "title": "Test Article",
            "url": "https://example.com",
            "score": 100,
            "by": "testuser",
            "time": 1234567890,
            "descendants": 50
        }
        respx.get("https://hacker-news.firebaseio.com/v0/item/1.json").mock(
            return_value=Response(200, json=item_data)
        )
        
        async with HackerNewsFetcher() as fetcher:
            article = await fetcher.fetch_item(1)
            
        assert article is not None
        assert article.title == "Test Article"
        assert article.url == "https://example.com"
        assert article.score == 100
    
    def test_calculate_relevance_score(self):
        """Test relevance score calculation."""
        fetcher = HackerNewsFetcher()
        
        # Article with MCP keyword
        article1 = Article(
            id=1,
            title="New MCP Protocol Released",
            url="https://example.com",
            text=None,
            score=150,
            by="user1",
            time=1234567890
        )
        score1, keywords1 = fetcher.calculate_relevance_score(article1)
        assert score1 > 0
        assert "MCP" in keywords1
        
        # Article with multiple keywords
        article2 = Article(
            id=2,
            title="AI and Robotics Startup Disruption",
            url="https://example.com",
            text=None,
            score=200,
            by="user2",
            time=1234567890
        )
        score2, keywords2 = fetcher.calculate_relevance_score(article2)
        assert score2 > score1  # Multiple keywords should score higher
        assert len(keywords2) > 1
    
    @pytest.mark.asyncio
    @respx.mock
    async def test_get_top_article(self):
        """Test getting the most relevant article."""
        # Mock top stories response
        respx.get("https://hacker-news.firebaseio.com/v0/topstories.json").mock(
            return_value=Response(200, json=[1, 2, 3])
        )
        
        # Mock individual items
        respx.get("https://hacker-news.firebaseio.com/v0/item/1.json").mock(
            return_value=Response(200, json={
                "id": 1, "type": "story", "title": "Random News",
                "score": 50, "by": "user1", "time": 1234567890
            })
        )
        respx.get("https://hacker-news.firebaseio.com/v0/item/2.json").mock(
            return_value=Response(200, json={
                "id": 2, "type": "story", "title": "MCP and AI News",
                "score": 100, "by": "user2", "time": 1234567890
            })
        )
        respx.get("https://hacker-news.firebaseio.com/v0/item/3.json").mock(
            return_value=Response(200, json={
                "id": 3, "type": "story", "title": "Other Tech News",
                "score": 75, "by": "user3", "time": 1234567890
            })
        )
        
        async with HackerNewsFetcher() as fetcher:
            result = await fetcher.get_top_article()
            
        assert result is not None
        article, keywords = result
        assert article.title == "MCP and AI News"  # Should pick the one with keywords
        assert len(keywords) > 0


class TestGitHubTrendingFetcher:
    """Test GitHub trending fetcher."""
    
    def test_parse_trending_repos(self):
        """Test parsing HTML to extract repositories."""
        fetcher = GitHubTrendingFetcher()
        
        # Sample HTML structure similar to GitHub trending page
        html = '''
        <article class="Box-row">
            <h2 class="h3 lh-condensed">
                <a href="/owner/repo-name">owner / repo-name</a>
            </h2>
            <p class="col-9 color-fg-muted my-1 pr-4">
                This is a description with MCP support
            </p>
            <span itemprop="programmingLanguage">Python</span>
            <a class="Link--muted d-inline-block mr-3" href="/owner/repo-name/stargazers">
                <svg></svg> 1,234
            </a>
            <span class="float-sm-right">
                <svg></svg> 123 stars today
            </span>
        </article>
        '''
        
        repos = fetcher.parse_trending_repos(html)
        assert len(repos) == 1
        
        repo = repos[0]
        assert repo.owner == "owner"
        assert repo.name == "repo-name"
        assert "MCP" in repo.description
        assert repo.language == "Python"
        assert repo.total_stars == 1234
        assert repo.stars_today == 123
    
    def test_find_mcp_repo(self):
        """Test finding MCP-related repositories."""
        fetcher = GitHubTrendingFetcher()
        
        repos = [
            TrendingRepo(
                owner="user1", name="regular-repo",
                url="https://github.com/user1/regular-repo",
                description="A regular repository",
                language="Python", stars_today=10, total_stars=100
            ),
            TrendingRepo(
                owner="user2", name="mcp-tool",
                url="https://github.com/user2/mcp-tool",
                description="A tool for something",
                language="Go", stars_today=50, total_stars=500
            ),
            TrendingRepo(
                owner="user3", name="another-repo",
                url="https://github.com/user3/another-repo",
                description="Implements Model Context Protocol",
                language="JavaScript", stars_today=30, total_stars=300
            ),
        ]
        
        # Should find by name
        mcp_repo = fetcher.find_mcp_repo(repos)
        assert mcp_repo is not None
        assert mcp_repo.name == "mcp-tool"
        
        # Should find by description
        repos_desc = [repos[0], repos[2]]  # Remove the name match
        mcp_repo2 = fetcher.find_mcp_repo(repos_desc)
        assert mcp_repo2 is not None
        assert "Model Context Protocol" in mcp_repo2.description


class TestCountriesFetcher:
    """Test countries fetcher."""
    
    @pytest.mark.asyncio
    async def test_load_countries(self):
        """Test loading countries from CSV."""
        async with CountriesFetcher() as fetcher:
            countries = fetcher.load_countries()
            
        assert len(countries) > 0
        
        # Check first country (Afghanistan)
        first_country = countries[0]
        assert first_country.name == "Afghanistan"
        assert first_country.capital == "Kabul"
        assert first_country.region == "Asia"
        assert first_country.population > 0
    
    @pytest.mark.asyncio
    async def test_get_random_country(self):
        """Test getting a random country."""
        async with CountriesFetcher() as fetcher:
            result = await fetcher.get_random_country()
            
        assert result is not None
        country, location_desc = result
        
        assert country.name != ""
        assert country.capital != ""
        assert len(location_desc) > 0
    
    def test_country_location_description(self):
        """Test country location description generation."""
        from src.fetchers.countries import Country
        
        country = Country(
            name="Test Country",
            capital="Test Capital",
            region="Europe",
            subregion="Western Europe",
            population=1000000,
            area=50000,
            languages=["English"],
            currencies=["Euro"],
            lat=52.5,
            lng=13.4
        )
        
        desc = country.get_location_description()
        assert "Test Capital" in desc
        assert "Test Country" in desc
        assert "Western Europe" in desc
        assert "Northern Hemisphere" in desc
        assert "European continent" in desc
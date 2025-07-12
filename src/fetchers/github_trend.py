"""GitHub trending repositories fetcher."""
import re
from dataclasses import dataclass
from typing import List, Optional

import httpx
from bs4 import BeautifulSoup

from ..utils.logger import get_logger
from ..utils.retry import async_retry

logger = get_logger(__name__)

GITHUB_TRENDING_URL = "https://github.com/trending"


@dataclass
class TrendingRepo:
    """Represents a trending GitHub repository."""
    owner: str
    name: str
    url: str
    description: str
    language: Optional[str]
    stars_today: Optional[int]
    total_stars: Optional[int]
    
    @property
    def full_name(self) -> str:
        """Get full repository name."""
        return f"{self.owner}/{self.name}"


class GitHubTrendingFetcher:
    """Fetches trending repositories from GitHub."""
    
    def __init__(self):
        """Initialize the GitHub trending fetcher."""
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            }
        )
        
    async def __aenter__(self):
        """Async context manager entry."""
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.client.aclose()
    
    @async_retry(max_attempts=3, initial_delay=2.0)
    async def fetch_trending_page(self) -> str:
        """Fetch the GitHub trending page HTML.
        
        Returns:
            HTML content of the trending page
        """
        response = await self.client.get(GITHUB_TRENDING_URL)
        response.raise_for_status()
        
        logger.info("Fetched GitHub trending page")
        return response.text
    
    def parse_trending_repos(self, html: str) -> List[TrendingRepo]:
        """Parse trending repositories from HTML.
        
        Args:
            html: HTML content of the trending page
            
        Returns:
            List of trending repositories
        """
        soup = BeautifulSoup(html, 'lxml')
        repos = []
        
        # Find all repository articles
        repo_articles = soup.find_all('article', class_='Box-row')
        
        for article in repo_articles:
            try:
                # Extract repository info
                h2 = article.find('h2', class_='h3')
                if not h2:
                    continue
                    
                repo_link = h2.find('a')
                if not repo_link:
                    continue
                    
                # Parse owner and name from href
                href = repo_link.get('href', '')
                parts = href.strip('/').split('/')
                if len(parts) != 2:
                    continue
                    
                owner, name = parts
                
                # Get description
                desc_p = article.find('p', class_='col-9')
                description = desc_p.text.strip() if desc_p else ""
                
                # Get language
                lang_span = article.find('span', itemprop='programmingLanguage')
                language = lang_span.text.strip() if lang_span else None
                
                # Get star counts
                stars_text = ""
                star_links = article.find_all('a', class_='Link--muted')
                for link in star_links:
                    if 'stargazers' in link.get('href', ''):
                        stars_text = link.text.strip()
                        break
                
                # Parse total stars
                total_stars = None
                if stars_text:
                    stars_match = re.search(r'([\d,]+)', stars_text)
                    if stars_match:
                        total_stars = int(stars_match.group(1).replace(',', ''))
                
                # Get stars today
                stars_today = None
                float_right = article.find('span', class_='float-sm-right')
                if float_right:
                    today_match = re.search(r'([\d,]+)\s+stars?\s+today', float_right.text)
                    if today_match:
                        stars_today = int(today_match.group(1).replace(',', ''))
                
                repo = TrendingRepo(
                    owner=owner,
                    name=name,
                    url=f"https://github.com/{owner}/{name}",
                    description=description,
                    language=language,
                    stars_today=stars_today,
                    total_stars=total_stars,
                )
                
                repos.append(repo)
                
            except Exception as e:
                logger.warning(f"Failed to parse repository: {e}")
                continue
        
        logger.info(f"Parsed {len(repos)} trending repositories")
        return repos
    
    def find_mcp_repo(self, repos: List[TrendingRepo]) -> Optional[TrendingRepo]:
        """Find the top MCP-related repository.
        
        Args:
            repos: List of trending repositories
            
        Returns:
            The top MCP repository or None
        """
        mcp_keywords = ['mcp', 'model-context-protocol', 'modelcontextprotocol']
        
        for repo in repos:
            # Check repo name
            if any(keyword in repo.name.lower() for keyword in mcp_keywords):
                logger.info(f"Found MCP repo by name: {repo.full_name}")
                return repo
                
            # Check description
            if any(keyword in repo.description.lower() for keyword in mcp_keywords):
                logger.info(f"Found MCP repo by description: {repo.full_name}")
                return repo
        
        logger.warning("No MCP repository found in trending")
        return None
    
    async def get_top_mcp_repo(self) -> Optional[TrendingRepo]:
        """Get the top trending MCP repository.
        
        Returns:
            The top MCP repository or None
        """
        try:
            # Fetch trending page
            html = await self.fetch_trending_page()
            
            # Parse repositories
            repos = self.parse_trending_repos(html)
            
            if not repos:
                logger.error("No repositories parsed from trending page")
                return None
            
            # Find MCP repo
            mcp_repo = self.find_mcp_repo(repos)
            
            if not mcp_repo:
                # If no MCP repo, could return the top repo as fallback
                logger.info("No MCP repo found, returning None")
                return None
            
            return mcp_repo
            
        except Exception as e:
            logger.error(f"Failed to get top MCP repo: {e}")
            return None
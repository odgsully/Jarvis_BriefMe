"""Hacker News fetcher for top articles."""
import asyncio
from dataclasses import dataclass
from typing import List, Optional, Tuple

import httpx

from ..utils.logger import get_logger
from ..utils.retry import async_retry

logger = get_logger(__name__)

HN_API_BASE = "https://hacker-news.firebaseio.com/v0"
KEYWORDS = ["3D", "MCP", "robotics", "startup", "AI", "disruption", "artificial intelligence", "machine learning"]


@dataclass
class Article:
    """Represents a Hacker News article."""
    id: int
    title: str
    url: Optional[str]
    text: Optional[str]
    score: int
    by: str
    time: int
    descendants: int = 0
    
    @property
    def content_url(self) -> str:
        """Get the URL to fetch content from."""
        return self.url or f"https://news.ycombinator.com/item?id={self.id}"


class HackerNewsFetcher:
    """Fetches and filters top Hacker News articles."""
    
    def __init__(self):
        """Initialize the HN fetcher."""
        self.client = httpx.AsyncClient(timeout=30.0)
        
    async def __aenter__(self):
        """Async context manager entry."""
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.client.aclose()
    
    @async_retry(max_attempts=3, initial_delay=1.0)
    async def fetch_top_stories(self, limit: int = 10) -> List[int]:
        """Fetch top story IDs from Hacker News.
        
        Args:
            limit: Number of top stories to fetch
            
        Returns:
            List of story IDs
        """
        url = f"{HN_API_BASE}/topstories.json"
        response = await self.client.get(url)
        response.raise_for_status()
        
        story_ids = response.json()
        logger.info(f"Fetched {len(story_ids)} top story IDs")
        
        return story_ids[:limit]
    
    @async_retry(max_attempts=3, initial_delay=1.0)
    async def fetch_item(self, item_id: int) -> Optional[Article]:
        """Fetch details for a specific item.
        
        Args:
            item_id: HN item ID
            
        Returns:
            Article object or None if fetch failed
        """
        url = f"{HN_API_BASE}/item/{item_id}.json"
        
        try:
            response = await self.client.get(url)
            response.raise_for_status()
            
            data = response.json()
            if not data or data.get('type') != 'story':
                return None
                
            return Article(
                id=data['id'],
                title=data.get('title', ''),
                url=data.get('url'),
                text=data.get('text'),
                score=data.get('score', 0),
                by=data.get('by', 'unknown'),
                time=data.get('time', 0),
                descendants=data.get('descendants', 0),
            )
            
        except Exception as e:
            logger.error(f"Failed to fetch item {item_id}: {e}")
            return None
    
    def calculate_relevance_score(self, article: Article) -> Tuple[float, List[str]]:
        """Calculate relevance score based on keywords.
        
        Args:
            article: Article to score
            
        Returns:
            Tuple of (score, matched_keywords)
        """
        title_lower = article.title.lower()
        matched_keywords = []
        
        # Check for keyword matches
        for keyword in KEYWORDS:
            if keyword.lower() in title_lower:
                matched_keywords.append(keyword)
        
        # Calculate score
        base_score = len(matched_keywords) * 10
        
        # Bonus for multiple matches
        if len(matched_keywords) > 1:
            base_score += 5
            
        # Small bonus for high HN score
        if article.score > 100:
            base_score += 2
        elif article.score > 50:
            base_score += 1
            
        return base_score, matched_keywords
    
    async def get_top_article(self) -> Optional[Tuple[Article, List[str]]]:
        """Get the most relevant article from top 10 HN stories.
        
        Returns:
            Tuple of (Article, matched_keywords) or None
        """
        try:
            # Fetch top story IDs
            story_ids = await self.fetch_top_stories(limit=10)
            
            # Fetch all articles concurrently
            tasks = [self.fetch_item(story_id) for story_id in story_ids]
            articles = await asyncio.gather(*tasks)
            
            # Filter out None values
            valid_articles = [a for a in articles if a is not None]
            
            if not valid_articles:
                logger.error("No valid articles fetched")
                return None
            
            # Score all articles
            scored_articles = []
            for article in valid_articles:
                score, keywords = self.calculate_relevance_score(article)
                scored_articles.append((score, article, keywords))
            
            # Sort by score (descending)
            scored_articles.sort(key=lambda x: x[0], reverse=True)
            
            # Get the best match
            best_score, best_article, best_keywords = scored_articles[0]
            
            # If no keywords matched, just return the top story
            if best_score == 0:
                logger.info("No keyword matches found, returning top story")
                return valid_articles[0], []
            
            logger.info(
                f"Selected article: {best_article.title}",
                score=best_score,
                keywords=best_keywords,
            )
            
            return best_article, best_keywords
            
        except Exception as e:
            logger.error(f"Failed to get top article: {e}")
            return None
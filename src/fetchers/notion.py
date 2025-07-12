"""Notion API fetcher for transcripts and quiz databases."""
import asyncio
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import httpx

from ..settings import settings
from ..utils.logger import get_logger
from ..utils.retry import async_retry

logger = get_logger(__name__)

# Notion database IDs
TRANSCRIPT_DB_ID = "22ccf08f4499809098b1d75b8650bb49"
CS_TERMS_DB_ID = "208cf08f449980ff800cd3b0abdd8562"
SPANISH_DB_ID = "21ecf08f449980ff8773f62dcd28f6ec"


@dataclass
class TranscriptRecord:
    """Represents a transcript record from Notion."""
    id: str
    date: datetime
    url: str
    title: Optional[str] = None


@dataclass
class CSTermRecord:
    """Represents a CS term from Notion."""
    id: str
    term: str
    definition: str
    category: Optional[str] = None


@dataclass
class SpanishRecord:
    """Represents a Spanish phrase from Notion."""
    id: str
    english: str
    spanish: str
    category: Optional[str] = None


class NotionFetcher:
    """Fetches data from Notion databases."""
    
    def __init__(self):
        """Initialize the Notion fetcher."""
        self.api_key = settings.notion_api_key
        
        # Debug API key format
        logger.info(
            "Initializing Notion fetcher",
            api_key_length=len(self.api_key) if self.api_key else 0,
            api_key_prefix=self.api_key[:20] if self.api_key else "None",
            api_key_has_secret_prefix=self.api_key.startswith("secret_") if self.api_key else False
        )
        
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Notion-Version": "2022-06-28",
                "Content-Type": "application/json",
            }
        )
        
    async def __aenter__(self):
        """Async context manager entry."""
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.client.aclose()
    
    async def test_api_connection(self) -> bool:
        """Test if the API key and connection are working.
        
        Returns:
            True if connection works, False otherwise
        """
        try:
            response = await self.client.get("https://api.notion.com/v1/users/me")
            if response.status_code == 200:
                user_data = response.json()
                logger.info(
                    "Notion API connection successful",
                    user_name=user_data.get("name", "Unknown"),
                    user_type=user_data.get("type", "Unknown")
                )
                return True
            else:
                logger.error(
                    "Notion API connection failed",
                    status_code=response.status_code,
                    response_text=response.text
                )
                return False
        except Exception as e:
            logger.error(f"Notion API connection test failed: {e}")
            return False
    
    @async_retry(max_attempts=3, initial_delay=1.0)
    async def query_database(
        self,
        database_id: str,
        filter_obj: Optional[Dict[str, Any]] = None,
        sorts: Optional[List[Dict[str, Any]]] = None,
        page_size: int = 100,
    ) -> List[Dict[str, Any]]:
        """Query a Notion database.
        
        Args:
            database_id: Notion database ID
            filter_obj: Optional filter object
            sorts: Optional sort configuration
            page_size: Number of results per page
            
        Returns:
            List of page objects
        """
        url = f"https://api.notion.com/v1/databases/{database_id}/query"
        
        results = []
        has_more = True
        start_cursor = None
        
        while has_more:
            payload = {
                "page_size": page_size,
            }
            
            if filter_obj:
                payload["filter"] = filter_obj
            if sorts:
                payload["sorts"] = sorts
            if start_cursor:
                payload["start_cursor"] = start_cursor
            
            response = await self.client.post(url, json=payload)
            
            # Enhanced error logging for 401s
            if response.status_code == 401:
                logger.error(
                    f"Notion API authentication failed",
                    database_id=database_id,
                    status_code=response.status_code,
                    response_text=response.text,
                    api_key_prefix=self.api_key[:20] if self.api_key else "None",
                    headers_sent=dict(response.request.headers)
                )
            
            response.raise_for_status()
            
            data = response.json()
            results.extend(data.get("results", []))
            
            has_more = data.get("has_more", False)
            start_cursor = data.get("next_cursor")
        
        logger.info(f"Fetched {len(results)} records from database {database_id}")
        return results
    
    async def fetch_transcripts_last_week(self) -> List[TranscriptRecord]:
        """Fetch transcript records from the last 7 days.
        
        Returns:
            List of transcript records
        """
        # Calculate date 7 days ago
        week_ago = datetime.now(timezone.utc) - timedelta(days=7)
        
        # Build filter for last 7 days
        filter_obj = {
            "property": "Date",
            "date": {
                "on_or_after": week_ago.isoformat()
            }
        }
        
        # Sort by date descending
        sorts = [
            {
                "property": "Date",
                "direction": "descending"
            }
        ]
        
        try:
            results = await self.query_database(
                TRANSCRIPT_DB_ID,
                filter_obj=filter_obj,
                sorts=sorts
            )
            
            transcripts = []
            for page in results:
                try:
                    # Extract properties
                    props = page.get("properties", {})
                    
                    # Get date
                    date_prop = props.get("Date", {})
                    date_str = date_prop.get("date", {}).get("start")
                    if not date_str:
                        continue
                    date_obj = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                    
                    # Get URL
                    url_prop = props.get("URL", {})
                    url = ""
                    if url_prop.get("type") == "url":
                        url = url_prop.get("url", "")
                    elif url_prop.get("type") == "rich_text":
                        rich_text = url_prop.get("rich_text", [])
                        if rich_text:
                            url = rich_text[0].get("plain_text", "")
                    
                    if not url:
                        continue
                    
                    # Get title if available
                    title_prop = props.get("Title", {}) or props.get("Name", {})
                    title = None
                    if title_prop.get("type") == "title":
                        title_list = title_prop.get("title", [])
                        if title_list:
                            title = title_list[0].get("plain_text", "")
                    
                    transcript = TranscriptRecord(
                        id=page["id"],
                        date=date_obj,
                        url=url,
                        title=title,
                    )
                    transcripts.append(transcript)
                    
                except Exception as e:
                    logger.warning(f"Failed to parse transcript record: {e}")
                    continue
            
            logger.info(f"Found {len(transcripts)} transcripts from last week")
            return transcripts
            
        except Exception as e:
            logger.error(f"Failed to fetch transcripts: {e}")
            return []
    
    async def fetch_all_cs_terms(self) -> List[CSTermRecord]:
        """Fetch all CS terms from the database.
        
        Returns:
            List of CS term records
        """
        try:
            results = await self.query_database(CS_TERMS_DB_ID)
            
            terms = []
            for page in results:
                try:
                    props = page.get("properties", {})
                    
                    # Get term
                    term_prop = props.get("Term", {}) or props.get("Name", {})
                    term = ""
                    if term_prop.get("type") == "title":
                        title_list = term_prop.get("title", [])
                        if title_list:
                            term = title_list[0].get("plain_text", "")
                    elif term_prop.get("type") == "rich_text":
                        rich_text = term_prop.get("rich_text", [])
                        if rich_text:
                            term = rich_text[0].get("plain_text", "")
                    
                    # Get definition
                    def_prop = props.get("Definition", {})
                    definition = ""
                    if def_prop.get("type") == "rich_text":
                        rich_text = def_prop.get("rich_text", [])
                        if rich_text:
                            definition = rich_text[0].get("plain_text", "")
                    
                    # Get category if available
                    cat_prop = props.get("Category", {})
                    category = None
                    if cat_prop.get("type") == "select":
                        select = cat_prop.get("select", {})
                        if select:
                            category = select.get("name", "")
                    
                    if term and definition:
                        cs_term = CSTermRecord(
                            id=page["id"],
                            term=term,
                            definition=definition,
                            category=category,
                        )
                        terms.append(cs_term)
                    
                except Exception as e:
                    logger.warning(f"Failed to parse CS term record: {e}")
                    continue
            
            logger.info(f"Fetched {len(terms)} CS terms")
            return terms
            
        except Exception as e:
            logger.error(f"Failed to fetch CS terms: {e}")
            return []
    
    async def fetch_all_spanish_phrases(self) -> List[SpanishRecord]:
        """Fetch all Spanish phrases from the database.
        
        Returns:
            List of Spanish phrase records
        """
        try:
            results = await self.query_database(SPANISH_DB_ID)
            
            phrases = []
            for page in results:
                try:
                    props = page.get("properties", {})
                    
                    # Get English phrase
                    eng_prop = props.get("En ingles", {}) or props.get("English", {})
                    english = ""
                    if eng_prop.get("type") in ["rich_text", "title"]:
                        text_list = eng_prop.get("rich_text", []) or eng_prop.get("title", [])
                        if text_list:
                            english = text_list[0].get("plain_text", "")
                    
                    # Get Spanish phrase
                    esp_prop = props.get("En español", {}) or props.get("Spanish", {})
                    spanish = ""
                    if esp_prop.get("type") == "rich_text":
                        rich_text = esp_prop.get("rich_text", [])
                        if rich_text:
                            spanish = rich_text[0].get("plain_text", "")
                    
                    # Get category if available
                    cat_prop = props.get("Category", {})
                    category = None
                    if cat_prop.get("type") == "select":
                        select = cat_prop.get("select", {})
                        if select:
                            category = select.get("name", "")
                    
                    if english and spanish:
                        phrase = SpanishRecord(
                            id=page["id"],
                            english=english,
                            spanish=spanish,
                            category=category,
                        )
                        phrases.append(phrase)
                    
                except Exception as e:
                    logger.warning(f"Failed to parse Spanish phrase record: {e}")
                    continue
            
            logger.info(f"Fetched {len(phrases)} Spanish phrases")
            return phrases
            
        except Exception as e:
            logger.error(f"Failed to fetch Spanish phrases: {e}")
            return []
    
    async def download_transcript(self, url: str, output_dir: Path) -> Optional[Path]:
        """Download a transcript from URL and save to file.
        
        Args:
            url: URL to download from
            output_dir: Directory to save transcript
            
        Returns:
            Path to saved file or None if failed
        """
        try:
            # Find the next available transcript number
            existing_files = list(output_dir.glob("transcript*.txt"))
            max_num = 0
            for file in existing_files:
                match = re.search(r'transcript(\d+)\.txt', file.name)
                if match:
                    num = int(match.group(1))
                    max_num = max(max_num, num)
            
            next_num = max_num + 1
            filename = f"transcript{next_num}.txt"
            filepath = output_dir / filename
            
            # Download content
            async with httpx.AsyncClient() as client:
                response = await client.get(url, follow_redirects=True)
                response.raise_for_status()
                
                # Save to file
                filepath.write_text(response.text, encoding='utf-8')
                
                logger.info(f"Downloaded transcript to {filepath}")
                return filepath
                
        except Exception as e:
            logger.error(f"Failed to download transcript from {url}: {e}")
            return None
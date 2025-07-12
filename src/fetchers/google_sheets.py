"""Google Sheets fetcher for transcripts and quiz data."""
import asyncio
import random
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import gspread
from google.auth.exceptions import GoogleAuthError

from ..settings import settings
from ..utils.logger import get_logger
from ..utils.retry import async_retry
from .transcript_processor import TranscriptProcessor

logger = get_logger(__name__)

# Google Sheets document ID (from the URL)
SHEETS_DOCUMENT_ID = "1pMNR5i3v1T-N63QnR_03X7ARWRR9PWJ3j0NP_jd4d7M"


@dataclass
class TranscriptRecord:
    """Represents a transcript record from Google Sheets."""
    id: str
    date: datetime
    url: str
    title: Optional[str] = None


@dataclass
class CSTermRecord:
    """Represents a CS term from Google Sheets."""
    id: str
    term: str
    definition: str
    category: Optional[str] = None


@dataclass
class SpanishRecord:
    """Represents a Spanish phrase from Google Sheets."""
    id: str
    english: str
    spanish: str
    category: Optional[str] = None


class GoogleSheetsFetcher:
    """Fetches data from Google Sheets via gspread."""
    
    def __init__(self):
        """Initialize the Google Sheets fetcher."""
        self.client = None
        self.document = None
        
    async def __aenter__(self):
        """Async context manager entry."""
        await self._connect()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        # gspread doesn't require explicit cleanup
        pass
    
    async def _connect(self) -> bool:
        """Connect to Google Sheets using CSV export URLs for public access.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            # For public sheets, we can access CSV export URLs directly
            # This bypasses the need for authentication
            logger.info("Using CSV export URLs for Google Sheets access")
            self.client = "csv_mode"  # Indicate we're using CSV mode
            self.document = SHEETS_DOCUMENT_ID
            return True
                
        except Exception as e:
            logger.error(f"Google Sheets connection failed: {e}")
            return False
    
    async def _find_sheet_gid(self, sheet_name: str) -> str:
        """Try to find the correct GID for a worksheet by trying different values."""
        import httpx
        
        # Common GID patterns to try
        gids_to_try = ["0", "1", "2", "3", "4", "5"]
        
        for gid in gids_to_try:
            try:
                csv_url = f"https://docs.google.com/spreadsheets/d/{self.document}/export?format=csv&gid={gid}"
                async with httpx.AsyncClient() as client:
                    response = await client.get(csv_url, follow_redirects=True)
                    if response.status_code == 200 and response.text.strip():
                        # Check if this looks like the right sheet by examining headers
                        lines = response.text.strip().split('\n')
                        if lines:
                            headers = lines[0].lower()
                            if sheet_name == "Transcript_Summaries" and ("date" in headers or "url" in headers or "title" in headers):
                                logger.info(f"Found GID {gid} for worksheet '{sheet_name}'")
                                return gid
                            elif sheet_name == "cs_terms" and ("term" in headers or "definition" in headers):
                                logger.info(f"Found GID {gid} for worksheet '{sheet_name}'")
                                return gid
                            elif sheet_name == "espanol" and ("español" in headers or "ingles" in headers or "english" in headers or "spanish" in headers):
                                logger.info(f"Found GID {gid} for worksheet '{sheet_name}'")
                                return gid
            except Exception:
                continue
        
        logger.warning(f"Could not find valid GID for worksheet '{sheet_name}', using default '0'")
        return "0"

    @async_retry(max_attempts=3, initial_delay=1.0)
    async def _get_worksheet_data(self, sheet_name: str) -> List[Dict[str, Any]]:
        """Get all data from a specific worksheet using CSV export.
        
        Args:
            sheet_name: Name of the worksheet to fetch
            
        Returns:
            List of row dictionaries
        """
        try:
            import httpx
            import csv
            import io
            import urllib.parse
            
            # URL encode the sheet name
            encoded_name = urllib.parse.quote(sheet_name)
            
            # Use the gviz URL format which works with sheet names
            csv_url = f"https://docs.google.com/spreadsheets/d/{self.document}/gviz/tq?tqx=out:csv&sheet={encoded_name}"
            
            async with httpx.AsyncClient() as client:
                response = await client.get(csv_url, follow_redirects=True)
                response.raise_for_status()
                
                # Parse CSV data - gviz format uses quoted CSV
                csv_content = response.text
                csv_reader = csv.DictReader(io.StringIO(csv_content))
                records = list(csv_reader)
            
            logger.info(f"Fetched {len(records)} records from worksheet '{sheet_name}' via CSV")
            return records
            
        except Exception as e:
            logger.error(f"Failed to fetch data from worksheet '{sheet_name}': {e}")
            return []
    
    async def fetch_transcripts_last_week(self) -> List[TranscriptRecord]:
        """Fetch transcript records from the last 7 days and process URLs for analysis.
        
        Returns:
            List of transcript records with analysis
        """
        try:
            records = await self._get_worksheet_data("Transcript_Summaries")
            
            # Calculate date 7 days ago
            week_ago = datetime.now(timezone.utc) - timedelta(days=7)
            
            transcripts = []
            transcript_processor = TranscriptProcessor()
            
            for i, record in enumerate(records):
                try:
                    # Parse date - handle various formats
                    date_str = record.get("Date", "").strip()
                    if not date_str:
                        continue
                    
                    # Try different date formats including MM.DD.YY
                    date_obj = None
                    for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y", "%m.%d.%y", "%Y-%m-%d %H:%M:%S"]:
                        try:
                            date_obj = datetime.strptime(date_str, fmt)
                            if date_obj.year < 100:  # Handle 2-digit years
                                date_obj = date_obj.replace(year=date_obj.year + 2000)
                            break
                        except ValueError:
                            continue
                    
                    if not date_obj:
                        logger.warning(f"Could not parse date: {date_str}")
                        continue
                    
                    # Add timezone info
                    if date_obj.tzinfo is None:
                        date_obj = date_obj.replace(tzinfo=timezone.utc)
                    
                    # Don't filter by date - process all URLs from the sheet
                    # if date_obj < week_ago:
                    #     continue
                    
                    # Get URL
                    url = record.get("URL", "").strip()
                    if not url:
                        continue
                    
                    # Process URL through transcript analysis
                    logger.info(f"Processing transcript URL: {url}")
                    analysis_result = await transcript_processor.process_url(url)
                    
                    if analysis_result:
                        # Use analysis as title
                        title = analysis_result
                    else:
                        title = f"Analysis failed for {url}"
                    
                    transcript = TranscriptRecord(
                        id=str(i),  # Use row index as ID
                        date=date_obj,
                        url=url,
                        title=title,  # This now contains the analysis
                    )
                    transcripts.append(transcript)
                    
                except Exception as e:
                    logger.warning(f"Failed to parse transcript record {i}: {e}")
                    continue
            
            # Sort by date descending
            transcripts.sort(key=lambda x: x.date, reverse=True)
            
            logger.info(f"Found {len(transcripts)} transcripts with analysis")
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
            records = await self._get_worksheet_data("cs_terms")
            
            terms = []
            for i, record in enumerate(records):
                try:
                    # CS Terms uses "Concept" and "Define" columns
                    term = record.get("Concept", "").strip()
                    definition = record.get("Define", "").strip()
                    category = record.get("Category", "").strip() or None
                    
                    if term and definition:
                        cs_term = CSTermRecord(
                            id=str(i),
                            term=term,
                            definition=definition,
                            category=category,
                        )
                        terms.append(cs_term)
                    
                except Exception as e:
                    logger.warning(f"Failed to parse CS term record {i}: {e}")
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
            records = await self._get_worksheet_data("espanol")
            
            phrases = []
            for i, record in enumerate(records):
                try:
                    # Get English phrase - column is "en ingles"
                    english = record.get("en ingles", "").strip()
                    
                    # Get Spanish phrase - column is "En español"
                    spanish = record.get("En español", "").strip()
                    category = record.get("Category", "").strip() or None
                    
                    if english and spanish:
                        phrase = SpanishRecord(
                            id=str(i),
                            english=english,
                            spanish=spanish,
                            category=category,
                        )
                        phrases.append(phrase)
                    
                except Exception as e:
                    logger.warning(f"Failed to parse Spanish phrase record {i}: {e}")
                    continue
            
            logger.info(f"Fetched {len(phrases)} Spanish phrases")
            return phrases
            
        except Exception as e:
            logger.error(f"Failed to fetch Spanish phrases: {e}")
            return []
    
    async def test_connection(self) -> bool:
        """Test if the Google Sheets connection is working.
        
        Returns:
            True if connection works, False otherwise
        """
        try:
            if not self.document:
                return False
                
            # Test CSV access by trying to fetch the first sheet
            import httpx
            csv_url = f"https://docs.google.com/spreadsheets/d/{self.document}/export?format=csv&gid=0"
            
            async with httpx.AsyncClient() as client:
                response = await client.get(csv_url, follow_redirects=True)
                response.raise_for_status()
            
            logger.info(
                "Google Sheets connection test successful",
                document_id=self.document,
                access_method="CSV export"
            )
            return True
            
        except Exception as e:
            logger.error(f"Google Sheets connection test failed: {e}")
            return False
"""Transcript processor for YouTube URLs and analysis integration."""
import asyncio
import re
import subprocess
import tempfile
from pathlib import Path
from typing import List, Optional, Tuple
from urllib.parse import urlparse, parse_qs

from ..utils.logger import get_logger
from ..utils.retry import async_retry
from .transcript_analytics import TranscriptAnalyzer, TranscriptAnalysis

logger = get_logger(__name__)


class TranscriptProcessor:
    """Processes YouTube URLs and runs transcript analysis."""
    
    def __init__(self):
        """Initialize the transcript processor."""
        self.paicc_dir = Path(__file__).parent.parent.parent / "paicc-2-copy"
        self.analyzer = TranscriptAnalyzer()
        
    def extract_youtube_id(self, url: str) -> Optional[str]:
        """Extract YouTube video ID from URL.
        
        Args:
            url: YouTube URL
            
        Returns:
            Video ID or None if not found
        """
        # Handle different YouTube URL formats
        patterns = [
            r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([^&\n?#]+)',
            r'youtube\.com/watch\?.*v=([^&\n?#]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        return None
    
    async def download_youtube_transcript(self, url: str) -> Optional[str]:
        """Download transcript from YouTube URL.
        
        Args:
            url: YouTube URL
            
        Returns:
            Transcript text or None if failed
        """
        try:
            video_id = self.extract_youtube_id(url)
            if not video_id:
                logger.error(f"Could not extract video ID from URL: {url}")
                return None
            
            # Try using yt-dlp to get transcript
            cmd = [
                "yt-dlp", 
                "--write-auto-sub", 
                "--write-sub", 
                "--sub-lang", "en", 
                "--skip-download",
                "--output", "%(title)s.%(ext)s",
                url
            ]
            
            # Create temporary directory
            with tempfile.TemporaryDirectory() as temp_dir:
                result = subprocess.run(
                    cmd, 
                    cwd=temp_dir,
                    capture_output=True, 
                    text=True, 
                    timeout=60
                )
                
                if result.returncode != 0:
                    logger.warning(f"yt-dlp failed for {url}: {result.stderr}")
                    # Try alternative method with youtube-transcript-api
                    return await self._try_transcript_api(video_id)
                
                # Look for subtitle files
                temp_path = Path(temp_dir)
                subtitle_files = list(temp_path.glob("*.vtt")) + list(temp_path.glob("*.srt"))
                
                if subtitle_files:
                    # Read the first subtitle file found
                    subtitle_file = subtitle_files[0]
                    with open(subtitle_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Clean up VTT/SRT formatting
                    transcript = self._clean_subtitle_text(content)
                    logger.info(f"Downloaded transcript for {url}: {len(transcript)} characters")
                    return transcript
                else:
                    logger.warning(f"No subtitle files found for {url}")
                    return await self._try_transcript_api(video_id)
                    
        except subprocess.TimeoutExpired:
            logger.error(f"Timeout downloading transcript for {url}")
            return None
        except Exception as e:
            logger.error(f"Error downloading transcript for {url}: {e}")
            return None
    
    async def _try_transcript_api(self, video_id: str) -> Optional[str]:
        """Try using youtube-transcript-api as fallback.
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            Transcript text or None if failed
        """
        try:
            # Try importing youtube-transcript-api
            from youtube_transcript_api import YouTubeTranscriptApi
            
            # Get transcript
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
            
            # Combine all text
            transcript_text = " ".join([item['text'] for item in transcript_list])
            
            logger.info(f"Downloaded transcript via API for {video_id}: {len(transcript_text)} characters")
            return transcript_text
            
        except ImportError:
            logger.warning("youtube-transcript-api not installed, cannot use fallback method")
            return None
        except Exception as e:
            logger.warning(f"youtube-transcript-api failed for {video_id}: {e}")
            return None
    
    def _clean_subtitle_text(self, content: str) -> str:
        """Clean VTT/SRT subtitle formatting.
        
        Args:
            content: Raw subtitle content
            
        Returns:
            Cleaned transcript text
        """
        # Remove VTT header
        content = re.sub(r'WEBVTT.*?\n\n', '', content, flags=re.DOTALL)
        
        # Remove timestamp lines
        content = re.sub(r'\d{2}:\d{2}:\d{2}\.\d{3} --> \d{2}:\d{2}:\d{2}\.\d{3}', '', content)
        content = re.sub(r'\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3}', '', content)
        
        # Remove sequence numbers
        content = re.sub(r'^\d+\s*$', '', content, flags=re.MULTILINE)
        
        # Remove HTML tags
        content = re.sub(r'<[^>]+>', '', content)
        
        # Clean up whitespace
        content = re.sub(r'\n+', ' ', content)
        content = re.sub(r'\s+', ' ', content)
        
        return content.strip()
    
    def save_transcript_file(self, transcript: str, url: str) -> Path:
        """Save transcript to numbered file in paicc-2 copy directory.
        
        Args:
            transcript: Transcript text
            url: Source URL for logging
            
        Returns:
            Path to saved transcript file
        """
        # Find next available transcript number
        existing_files = list(self.paicc_dir.glob("transcript*.txt"))
        numbers = []
        
        for file in existing_files:
            match = re.search(r'transcript(\d*).txt', file.name)
            if match:
                if match.group(1):  # transcript2.txt, transcript3.txt, etc.
                    numbers.append(int(match.group(1)))
                else:  # transcript.txt
                    numbers.append(1)
        
        next_number = max(numbers) + 1 if numbers else 1
        
        if next_number == 1:
            filename = "transcript.txt"
        else:
            filename = f"transcript{next_number}.txt"
        
        filepath = self.paicc_dir / filename
        
        # Write transcript to file
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(transcript)
        
        logger.info(f"Saved transcript from {url} to {filepath}")
        return filepath
    
    async def run_paicc_analysis(self, transcript_text: str, include_word_frequency: bool = False) -> Optional[TranscriptAnalysis]:
        """Run transcript analysis using OpenAI API.
        
        Args:
            transcript_text: Transcript text to analyze
            include_word_frequency: Whether to include word frequency analysis
            
        Returns:
            TranscriptAnalysis object or None if failed
        """
        try:
            # Run the analysis using our new analyzer
            analysis = await self.analyzer.analyze_transcript(
                transcript_text, 
                include_word_frequency=include_word_frequency,
                min_word_count=5
            )
            
            logger.info("Completed transcript analysis")
            return analysis
            
        except Exception as e:
            logger.error(f"Error running transcript analysis: {e}")
            return None
    
    
    async def process_url(self, url: str, include_word_frequency: bool = False) -> Optional[str]:
        """Process a URL through the complete pipeline.
        
        Args:
            url: YouTube URL to process
            include_word_frequency: Whether to include word frequency analysis
            
        Returns:
            Formatted analysis summary or None if failed
        """
        try:
            # Download transcript
            transcript = await self.download_youtube_transcript(url)
            if not transcript:
                # Return a message indicating transcript not available
                video_id = self.extract_youtube_id(url)
                return f"Transcript not available for video {video_id or 'unknown'}. The video may not have captions enabled or may be private/restricted."
            
            # Optionally save to file for debugging/reference
            # transcript_file = self.save_transcript_file(transcript, url)
            
            # Run analysis directly on transcript text
            analysis = await self.run_paicc_analysis(transcript, include_word_frequency)
            if not analysis:
                return f"Analysis failed for transcript from {url}"
            
            # Format results for briefing
            summary_parts = []
            
            if analysis.quick_summary:
                summary_parts.append(f"Summary: {analysis.quick_summary}")
            
            if analysis.bullet_point_highlights:
                summary_parts.append("Key Points:")
                for point in analysis.bullet_point_highlights[:3]:  # Limit to top 3
                    summary_parts.append(f"• {point}")
            
            if analysis.sentiment_analysis:
                summary_parts.append(f"Sentiment: {analysis.sentiment_analysis}")
            
            if analysis.keywords:
                summary_parts.append(f"Keywords: {', '.join(analysis.keywords[:5])}")  # Top 5 keywords
            
            return "\n".join(summary_parts)
            
        except Exception as e:
            logger.error(f"Error processing URL {url}: {e}")
            return f"Processing failed for {url}: {str(e)}"
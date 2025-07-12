"""
Transcript Analytics Module

This module provides advanced transcript analysis capabilities using OpenAI's GPT models
with structured output. It includes word frequency analysis and sentiment analysis.

Extracted from paicc-2 and integrated into the main project.
"""

import os
import json
from typing import List, Dict, Optional
from collections import Counter
import re

from pydantic import BaseModel, Field
from openai import AsyncOpenAI

from src.utils.logger import get_logger

logger = get_logger(__name__)


class TranscriptAnalysis(BaseModel):
    """Structured output model for transcript analysis."""
    quick_summary: str = Field(description="A concise summary of the transcript in 2-3 sentences")
    bullet_point_highlights: List[str] = Field(description="Key takeaways as bullet points")
    sentiment_analysis: str = Field(description="Overall sentiment/tone of the transcript")
    keywords: List[str] = Field(description="Important keywords or topics mentioned")
    word_frequencies: Optional[Dict[str, int]] = Field(default=None, description="Word frequency analysis")


class TranscriptAnalyzer:
    """Handles transcript analysis using OpenAI's API with structured outputs."""
    
    WORD_BLACKLIST = {
        'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them',
        'my', 'your', 'his', 'its', 'our', 'their', 'mine', 'yours', 'hers', 'ours', 'theirs',
        'this', 'that', 'these', 'those', 'which', 'who', 'whom', 'whose', 'what', 'where',
        'when', 'why', 'how', 'a', 'an', 'the', 'and', 'but', 'or', 'nor', 'for', 'yet',
        'so', 'is', 'am', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had',
        'do', 'does', 'did', 'will', 'would', 'shall', 'should', 'may', 'might', 'must',
        'can', 'could', 'to', 'of', 'in', 'on', 'at', 'by', 'from', 'up', 'out', 'off',
        'over', 'under', 'again', 'further', 'then', 'once', 'here', 'there', 'all', 'both',
        'each', 'few', 'more', 'most', 'other', 'some', 'such', 'no', 'not', 'only', 'own',
        'same', 'than', 'too', 'very', 's', 't', 'just', 'don', 'now', 'as', 'with',
        'about', 'after', 'also', 'back', 'before', 'between', 'during', 'even', 'first',
        'if', 'into', 'like', 'make', 'many', 'one', 'see', 'such', 'take', 'than', 'two',
        'want', 'way', 'well', 'because', 'get', 'go', 'good', 'know', 'last', 'new',
        'people', 'say', 'think', 'time', 'use', 'work', 'year', 'come', 'day', 'give'
    }
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-2024-08-06"):
        """Initialize the analyzer with OpenAI credentials."""
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OpenAI API key not found. Set OPENAI_API_KEY environment variable.")
        
        self.client = AsyncOpenAI(api_key=self.api_key)
        self.model = model
        logger.info(f"Initialized TranscriptAnalyzer with model: {model}")
    
    async def analyze_transcript(
        self, 
        transcript: str, 
        include_word_frequency: bool = False,
        min_word_count: int = 5
    ) -> TranscriptAnalysis:
        """
        Analyze a transcript using OpenAI's API.
        
        Args:
            transcript: The transcript text to analyze
            include_word_frequency: Whether to include word frequency analysis
            min_word_count: Minimum occurrences for a word to be included in frequency analysis
            
        Returns:
            TranscriptAnalysis object with the analysis results
        """
        logger.info("Starting transcript analysis")
        
        # Prepare the prompt
        prompt = f"""Please analyze the following transcript and provide:
1. A quick summary (2-3 sentences)
2. Key highlights as bullet points
3. Overall sentiment/tone analysis
4. Important keywords or topics

Transcript:
{transcript[:8000]}  # Limit to avoid token limits
"""
        
        try:
            # Make the API call with structured output
            response = await self.client.beta.chat.completions.parse(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a helpful transcript analyst. Provide concise, insightful analysis."},
                    {"role": "user", "content": prompt}
                ],
                response_format=TranscriptAnalysis,
                temperature=0.3,
                max_tokens=1000
            )
            
            # Extract the parsed response
            analysis = response.choices[0].message.parsed
            
            # Add word frequency analysis if requested
            if include_word_frequency:
                analysis.word_frequencies = self._analyze_word_frequency(transcript, min_word_count)
            
            logger.info("Transcript analysis completed successfully")
            return analysis
            
        except Exception as e:
            logger.error(f"Error during transcript analysis: {str(e)}")
            raise
    
    def _analyze_word_frequency(self, text: str, min_count: int = 5) -> Dict[str, int]:
        """
        Analyze word frequency in the transcript.
        
        Args:
            text: The text to analyze
            min_count: Minimum occurrences to include a word
            
        Returns:
            Dictionary of word frequencies
        """
        # Convert to lowercase and extract words
        words = re.findall(r'\b[a-z]+\b', text.lower())
        
        # Filter out blacklisted words
        filtered_words = [word for word in words if word not in self.WORD_BLACKLIST]
        
        # Count frequencies
        word_counts = Counter(filtered_words)
        
        # Filter by minimum count and return sorted
        return {
            word: count 
            for word, count in word_counts.most_common() 
            if count >= min_count
        }
    
    def format_analysis_text(self, analysis: TranscriptAnalysis) -> str:
        """
        Format the analysis results as human-readable text.
        
        Args:
            analysis: The TranscriptAnalysis object
            
        Returns:
            Formatted text string
        """
        output = []
        output.append("=== Transcript Analysis ===\n")
        
        output.append("Quick Summary:")
        output.append(f"{analysis.quick_summary}\n")
        
        output.append("Key Highlights:")
        for highlight in analysis.bullet_point_highlights:
            output.append(f"• {highlight}")
        output.append("")
        
        output.append("Sentiment Analysis:")
        output.append(f"{analysis.sentiment_analysis}\n")
        
        output.append("Keywords:")
        output.append(", ".join(analysis.keywords))
        
        if analysis.word_frequencies:
            output.append("\nWord Frequency Analysis:")
            max_count = max(analysis.word_frequencies.values())
            for word, count in list(analysis.word_frequencies.items())[:20]:  # Top 20 words
                bar_length = int((count / max_count) * 30)
                bar = "█" * bar_length
                output.append(f"{word:<15} {count:>4} {bar}")
        
        return "\n".join(output)
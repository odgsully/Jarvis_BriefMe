"""OpenAI GPT wrapper for content summarization."""
from typing import Dict, List, Optional

import openai
from openai import AsyncOpenAI

from ..settings import settings
from ..utils.logger import get_logger
from ..utils.retry import async_retry

logger = get_logger(__name__)

# Default word limits
DEFAULT_WORD_LIMIT = 200
SUMMARY_WORD_LIMIT = 150
KEYPOINTS_WORD_LIMIT = 100


class Summarizer:
    """Handles content summarization using OpenAI GPT."""
    
    def __init__(self):
        """Initialize the summarizer with OpenAI client."""
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        
    @async_retry(max_attempts=3, initial_delay=1.0)
    async def summarize(
        self,
        content: str,
        prompt_type: str = "summary",
        word_limit: int = DEFAULT_WORD_LIMIT,
        additional_context: Optional[str] = None,
    ) -> str:
        """Summarize content using GPT.
        
        Args:
            content: Content to summarize
            prompt_type: Type of summary (summary, keypoints, keywords, etc.)
            word_limit: Maximum words in response
            additional_context: Additional context for the prompt
            
        Returns:
            Summarized content
        """
        if not content:
            return "(No content to summarize)"
        
        # Build the appropriate prompt
        prompt = self._build_prompt(content, prompt_type, word_limit, additional_context)
        
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a concise and accurate summarizer."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=word_limit * 2,  # Rough estimate
            )
            
            result = response.choices[0].message.content.strip()
            
            logger.info(
                "Generated summary",
                prompt_type=prompt_type,
                input_length=len(content),
                output_length=len(result),
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to generate summary: {e}")
            return f"(Summary generation failed: {str(e)})"
    
    def _build_prompt(
        self,
        content: str,
        prompt_type: str,
        word_limit: int,
        additional_context: Optional[str],
    ) -> str:
        """Build the appropriate prompt based on type.
        
        Args:
            content: Content to process
            prompt_type: Type of processing needed
            word_limit: Word limit for response
            additional_context: Additional context
            
        Returns:
            Formatted prompt
        """
        base_prompts = {
            "summary": f"Summarize the following content in {word_limit} words or less:\n\n{content}",
            
            "keypoints": f"Extract the key facts and points from the following content as a bulleted list. Limit to {word_limit} words total:\n\n{content}",
            
            "keywords": f"List all relevant keywords and tags from the following content. Format as comma-separated values:\n\n{content}",
            
            "mcp_summary": f"Summarize this GitHub Model Context Protocol (MCP) repository in {word_limit} words or less. Focus on its purpose, features, and use cases:\n\n{content}",
            
            "codebase_summary": f"Provide a comprehensive summary of this codebase in {word_limit} words or less. Include the main directories, purpose, and key features:\n\n{content}",
            
            "fact": f"Generate an interesting and educational fact about {content}. Limit to {word_limit} words.",
            
            "golf_summary": f"Describe the most renowned golf courses/clubs in {content}. Include details about their location relative to major cities or landmarks using driving distances and directions (N/S/E/W). Limit to {word_limit} words.",
            
            "invention_summary": f"Provide a summary/history of {content}. Limit to {word_limit} words.",
            
            "gc_knowledge": f"Write a 2-paragraph excerpt about {content} that would be standard knowledge for general contractors working on commercial and residential developments. Make it practical and informative.",
            
            "movie_summary": f"Provide a brief {word_limit} word summary of the plot of {content}. Focus on the main storyline and key themes.",
            
            "score_summary": f"Provide a brief {word_limit} word summary about the musical score of {content}. Include the composer name if known.",
        }
        
        prompt = base_prompts.get(prompt_type, base_prompts["summary"])
        
        if additional_context:
            prompt = f"{additional_context}\n\n{prompt}"
            
        return prompt
    
    async def generate_fact(
        self,
        topic: str,
        fact_type: str,
        word_limit: int = DEFAULT_WORD_LIMIT,
    ) -> str:
        """Generate a fact about a specific topic.
        
        Args:
            topic: Topic to generate fact about
            fact_type: Type of fact (historical, technical, etc.)
            word_limit: Maximum words
            
        Returns:
            Generated fact
        """
        prompts = {
            "ww1": f"Generate an interesting and lesser-known fact about World War 1. Limit to {word_limit} words.",
            
            "ww2": f"Generate an interesting and lesser-known fact about World War 2. Limit to {word_limit} words.",
            
            "europe": f"Generate an interesting historical fact about Europe. Limit to {word_limit} words.",
            
            "ireland": f"Generate an interesting historical fact about Ireland. Limit to {word_limit} words.",
            
            "jerusalem": f"Generate an interesting historical fact about Jerusalem. Limit to {word_limit} words.",
            
            "india": f"Generate an interesting historical fact about India. Limit to {word_limit} words.",
            
            "mexico": f"Generate an interesting historical fact about Mexico. Limit to {word_limit} words.",
            
            "stunt_rigging": f"Generate an interesting fact or summary about stunt rigging in film/TV production. Limit to {word_limit} words.",
            
            "bike": f"Generate an interesting fact about dirt bikes or street motorcycles history. Limit to {word_limit} words.",
            
            "nasa_launch": f"Generate a fact about a NASA launch that occurred in the year {topic}. If no launches that year, mention the closest significant launch. Limit to {word_limit} words.",
            
            "gc": f"Generate practical general contractor knowledge about a random aspect of commercial or residential development. Make it a 2-paragraph excerpt with useful information.",
        }
        
        prompt = prompts.get(fact_type, f"Generate an interesting fact about {topic}. Limit to {word_limit} words.")
        
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a knowledgeable educator who provides interesting facts."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=word_limit * 2,
            )
            
            result = response.choices[0].message.content.strip()
            
            logger.info(
                "Generated fact",
                fact_type=fact_type,
                word_limit=word_limit,
                output_length=len(result),
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to generate fact: {e}")
            return f"(Fact generation failed: {str(e)})"
    
    async def batch_summarize(
        self,
        items: List[Dict[str, str]],
        word_limit: int = DEFAULT_WORD_LIMIT,
    ) -> Dict[str, str]:
        """Batch summarize multiple items.
        
        Args:
            items: List of dicts with 'key', 'content', and 'type'
            word_limit: Word limit for each summary
            
        Returns:
            Dict mapping keys to summaries
        """
        results = {}
        
        for item in items:
            key = item.get("key", "")
            content = item.get("content", "")
            prompt_type = item.get("type", "summary")
            
            if key and content:
                summary = await self.summarize(content, prompt_type, word_limit)
                results[key] = summary
                
        return results
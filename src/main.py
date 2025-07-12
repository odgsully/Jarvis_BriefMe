#!/usr/bin/env python3
"""Main orchestrator for Jarvis BriefMe daily briefing generation."""
import argparse
import asyncio
import random
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd

from .emailer import Emailer
from .fetchers.hn import HackerNewsFetcher
from .fetchers.github_trend import GitHubTrendingFetcher
from .fetchers.google_sheets import GoogleSheetsFetcher
from .fetchers.countries import CountriesFetcher
from .fetchers.languages import LanguageFetcher
from .file_writer import FileWriter
from .generators.cycle import CycleEngine
from .generators.codebase import CodebaseSelector
from .generators.summariser import Summarizer
from .settings import settings
from .template_engine import TemplateEngine
from .utils.logger import configure_logging, get_logger

logger = get_logger(__name__)

# Configure logging
configure_logging()


class BriefingOrchestrator:
    """Main orchestrator for daily briefing generation."""
    
    def __init__(self):
        """Initialize the orchestrator."""
        self.template_engine = TemplateEngine()
        self.file_writer = FileWriter()
        self.emailer = Emailer()
        self.cycle_engine = CycleEngine()
        self.summarizer = Summarizer()
        self.language_fetcher = LanguageFetcher()
        
        # Ensure directories exist
        settings.ensure_directories()
        
    async def gather_data(self) -> Dict[str, str]:
        """Gather all data for the daily briefing.
        
        Returns:
            Dictionary of all template context data
        """
        context = {}
        
        # Get current date
        now = datetime.now()
        context['FULLDATE'] = now.strftime("%A, %B %d, %Y")
        
        # Get cycle data
        year, state, days_left = self.cycle_engine.advance()
        context['CURRENT_STUDY_YEAR'] = str(year)
        context['CURRENT_STUDY_STATE'] = state
        context['DAYS_LEFT'] = str(days_left)
        
        # Add catchphrase
        context['GET_TO_IT_SAYING'] = "dive into"
        
        # Gather data from various sources
        await self._gather_hacker_news(context)
        await self._gather_github_trending(context)
        await self._gather_sheets_data(context)
        await self._gather_country_data(context)
        await self._gather_year_based_data(context, year)
        await self._gather_generated_facts(context, year, state)
        self._gather_language_section(context, now)
        
        return context
    
    async def _gather_hacker_news(self, context: Dict[str, str]) -> None:
        """Gather Hacker News data."""
        try:
            async with HackerNewsFetcher() as hn_fetcher:
                result = await hn_fetcher.get_top_article()
                
                if result:
                    article, keywords = result
                    context['YC_ARTICLE_PICK'] = article.title
                    context['YC_ARTICLE_KEYWORDS'] = ', '.join(keywords) if keywords else 'technology, startup'
                    
                    # Generate summary and keypoints
                    context['YC_ARTICLE_SUMMARY'] = await self.summarizer.summarize(
                        article.title, "summary", 150
                    )
                    context['YC_ARTICLE_KEYPOINTS'] = await self.summarizer.summarize(
                        article.title, "keypoints", 100
                    )
                else:
                    context['YC_ARTICLE_PICK'] = "(No article available)"
                    context['YC_ARTICLE_SUMMARY'] = "(Summary not available)"
                    context['YC_ARTICLE_KEYPOINTS'] = "(Key points not available)"
                    context['YC_ARTICLE_KEYWORDS'] = "(Keywords not available)"
                    
        except Exception as e:
            logger.error(f"Failed to gather Hacker News data: {e}")
            context['YC_ARTICLE_PICK'] = "(data unavailable)"
            context['YC_ARTICLE_SUMMARY'] = "(data unavailable)"
            context['YC_ARTICLE_KEYPOINTS'] = "(data unavailable)"
            context['YC_ARTICLE_KEYWORDS'] = "(data unavailable)"
    
    async def _gather_github_trending(self, context: Dict[str, str]) -> None:
        """Gather GitHub trending MCP data."""
        try:
            async with GitHubTrendingFetcher() as gh_fetcher:
                mcp_repo = await gh_fetcher.get_top_mcp_repo()
                
                if mcp_repo:
                    context['GITHUB_TRENDING_MCP_NAME'] = mcp_repo.full_name
                    context['GITHUB_TRENDING_MCP_SUMMARY'] = await self.summarizer.summarize(
                        mcp_repo.description, "mcp_summary", 150
                    )
                else:
                    context['GITHUB_TRENDING_MCP_NAME'] = "(No MCP repo found)"
                    context['GITHUB_TRENDING_MCP_SUMMARY'] = "(No MCP summary available)"
                    
        except Exception as e:
            logger.error(f"Failed to gather GitHub trending data: {e}")
            context['GITHUB_TRENDING_MCP_NAME'] = "(data unavailable)"
            context['GITHUB_TRENDING_MCP_SUMMARY'] = "(data unavailable)"
    
    async def _gather_sheets_data(self, context: Dict[str, str]) -> None:
        """Gather Google Sheets data for transcripts and quizzes."""
        try:
            async with GoogleSheetsFetcher() as sheets_fetcher:
                # Test connection first
                connection_working = await sheets_fetcher.test_connection()
                if not connection_working:
                    logger.error("Google Sheets connection failed, skipping all sheets data")
                    context['TRANSCRIPT_TABLE'] = "Google Sheets connection failed"
                    context['QUIZ_ME_CS_TERM'] = "CS quiz not available"
                    context['QUIZ_ME_ESPANOL'] = "Spanish quiz not available"
                    return
                
                # Get transcripts with analysis
                transcripts = await sheets_fetcher.fetch_transcripts_last_week()
                
                if transcripts:
                    transcript_lines = []
                    for transcript in transcripts[:3]:  # Limit to 3 most recent
                        date_str = transcript.date.strftime("%m/%d")
                        # The title now contains the full analysis
                        analysis = transcript.title or "No analysis available"
                        transcript_lines.append(f"Analysis for {date_str}:")
                        transcript_lines.append(analysis)
                        transcript_lines.append("")  # Add spacing
                    
                    context['TRANSCRIPT_TABLE'] = '\n'.join(transcript_lines)
                else:
                    context['TRANSCRIPT_TABLE'] = "No transcripts available for analysis"
                
                # Get CS quiz
                cs_terms = await sheets_fetcher.fetch_all_cs_terms()
                if cs_terms:
                    term = random.choice(cs_terms)
                    context['QUIZ_ME_CS_TERM'] = term.term
                    context['QUIZ_ME_CS_DEFINE'] = term.definition
                else:
                    context['QUIZ_ME_CS_TERM'] = "CS quiz not available"
                    context['QUIZ_ME_CS_DEFINE'] = "Definition not available"
                
                # Get Spanish quiz
                spanish_phrases = await sheets_fetcher.fetch_all_spanish_phrases()
                if spanish_phrases:
                    phrase = random.choice(spanish_phrases)
                    context['QUIZ_ME_ESPANOL'] = phrase.spanish
                    context['QuizMeIngles'] = phrase.english
                else:
                    context['QUIZ_ME_ESPANOL'] = "Spanish quiz not available"
                    context['QuizMeIngles'] = "English translation not available"
                    
        except Exception as e:
            logger.error(f"Failed to gather Google Sheets data: {e}")
            context['TRANSCRIPT_TABLE'] = "(data unavailable)"
            context['QUIZ_ME_CS_TERM'] = "(data unavailable)"
            context['QUIZ_ME_ESPANOL'] = "(data unavailable)"
    
    async def _gather_country_data(self, context: Dict[str, str]) -> None:
        """Gather random country data."""
        try:
            async with CountriesFetcher() as country_fetcher:
                result = await country_fetcher.get_random_country()
                
                if result:
                    country, location_desc = result
                    context['COUNTRY_OF_THE_DAY'] = country.name
                    context['COUNTRY_CAPITAL_OF_THE_DAY'] = country.capital
                    context['CAPITAL_LOCATION_BREAKDOWN'] = location_desc
                else:
                    context['COUNTRY_OF_THE_DAY'] = "(Country not available)"
                    context['COUNTRY_CAPITAL_OF_THE_DAY'] = "(Capital not available)"
                    context['CAPITAL_LOCATION_BREAKDOWN'] = "(Location not available)"
                    
        except Exception as e:
            logger.error(f"Failed to gather country data: {e}")
            context['COUNTRY_OF_THE_DAY'] = "(data unavailable)"
            context['COUNTRY_CAPITAL_OF_THE_DAY'] = "(data unavailable)"
            context['CAPITAL_LOCATION_BREAKDOWN'] = "(data unavailable)"
    
    async def _gather_year_based_data(self, context: Dict[str, str], year: int) -> None:
        """Gather data based on the current study year."""
        try:
            # Load Oscar data
            oscars_df = pd.read_csv(settings.datasets_dir / "Oscars.csv")
            oscar_row = oscars_df[oscars_df['Year'] == year]
            
            if not oscar_row.empty:
                row = oscar_row.iloc[0]
                context['CURRENT_YEAR_BEST_PICTURE'] = row['Best Picture']
                context['CURRENT_YEAR_BEST_ACTOR_IN_PICTURE'] = row['Best Actor']
                context['CURRENT_YEAR_BEST_CINEMATOGRAPHY'] = row['Best Cinematography']
                context['CURRENT_YEAR_BEST_SCORE'] = row['Best Score']
                context['CURRENT_YEAR_BEST_FOREIGN_FILM'] = row['Best Foreign Film']
                
                # Generate movie summaries with word limits from define_fields.txt
                context['CURRENT_YEAR_BEST_PICTURE_SUM'] = await self.summarizer.summarize(
                    row['Best Picture'], "movie_summary", 50
                )
                context['CURRENT_YEAR_BEST_ACTOR_IN_PICTURE_SUM'] = await self.summarizer.summarize(
                    row['Best Actor'], "movie_summary", 50
                )
                context['CURRENT_YEAR_BEST_CINEMATOGRAPHY_SUM'] = await self.summarizer.summarize(
                    row['Best Cinematography'], "movie_summary", 50
                )
                context['CURRENT_YEAR_BEST_SCORE_SUM'] = await self.summarizer.summarize(
                    row['Best Score'], "score_summary", 25
                )
                context['CURRENT_YEAR_BEST_FOREIGN_FILM_SUM'] = await self.summarizer.summarize(
                    row['Best Foreign Film'], "movie_summary", 50
                )
            else:
                context['CURRENT_YEAR_BEST_PICTURE'] = f"No Oscars ceremony held in {year}"
                context['CURRENT_YEAR_BEST_ACTOR_IN_PICTURE'] = f"No Oscars ceremony held in {year}"
                context['CURRENT_YEAR_BEST_CINEMATOGRAPHY'] = f"No Oscars ceremony held in {year}"
                context['CURRENT_YEAR_BEST_SCORE'] = f"No Oscars ceremony held in {year}"
                context['CURRENT_YEAR_BEST_FOREIGN_FILM'] = f"No Oscars ceremony held in {year}"
                context['CURRENT_YEAR_BEST_PICTURE_SUM'] = f"No Oscars ceremony held in {year}"
                context['CURRENT_YEAR_BEST_ACTOR_IN_PICTURE_SUM'] = f"No Oscars ceremony held in {year}"
                context['CURRENT_YEAR_BEST_CINEMATOGRAPHY_SUM'] = f"No Oscars ceremony held in {year}"
                context['CURRENT_YEAR_BEST_SCORE_SUM'] = f"No Oscars ceremony held in {year}"
                context['CURRENT_YEAR_BEST_FOREIGN_FILM_SUM'] = f"No Oscars ceremony held in {year}"
            
            # Load President data
            presidents_df = pd.read_csv(settings.datasets_dir / "Presidents.csv")
            president_row = presidents_df[presidents_df['Year'] == year]
            
            if not president_row.empty:
                row = president_row.iloc[0]
                context['CURRENT_YEAR_US_PRESIDENT_VPS'] = f"{row['President']} (President), {row['Vice President']} (Vice President)"
                context['NEW_MAJOR_PRESIDENTIAL_DECISION'] = row['Major Decision']
            else:
                context['CURRENT_YEAR_US_PRESIDENT_VPS'] = f"Presidential data not available for {year}"
                context['NEW_MAJOR_PRESIDENTIAL_DECISION'] = f"Presidential decision data not available for {year}"
            
            # Load Invention data
            inventions_df = pd.read_csv(settings.datasets_dir / "Inventions.csv")
            invention_row = inventions_df[inventions_df['Year'] == year]
            
            if not invention_row.empty:
                row = invention_row.iloc[0]
                context['MAJOR_INVENTION_OF_YEAR'] = row['Invention']
                context['MAJOR_INVENTION_SUMMARY'] = row['Summary']
            else:
                context['MAJOR_INVENTION_OF_YEAR'] = f"No major invention recorded for {year}"
                context['MAJOR_INVENTION_SUMMARY'] = f"No invention summary available for {year}"
                
        except Exception as e:
            logger.error(f"Failed to gather year-based data: {e}")
            context['CURRENT_YEAR_BEST_PICTURE'] = "(data unavailable)"
            context['CURRENT_YEAR_BEST_ACTOR_IN_PICTURE'] = "(data unavailable)"
            context['CURRENT_YEAR_BEST_CINEMATOGRAPHY'] = "(data unavailable)"
            context['CURRENT_YEAR_BEST_SCORE'] = "(data unavailable)"
            context['CURRENT_YEAR_BEST_FOREIGN_FILM'] = "(data unavailable)"
            context['CURRENT_YEAR_BEST_PICTURE_SUM'] = "(data unavailable)"
            context['CURRENT_YEAR_BEST_ACTOR_IN_PICTURE_SUM'] = "(data unavailable)"
            context['CURRENT_YEAR_BEST_CINEMATOGRAPHY_SUM'] = "(data unavailable)"
            context['CURRENT_YEAR_BEST_SCORE_SUM'] = "(data unavailable)"
            context['CURRENT_YEAR_BEST_FOREIGN_FILM_SUM'] = "(data unavailable)"
            context['CURRENT_YEAR_US_PRESIDENT_VPS'] = "(data unavailable)"
            context['NEW_MAJOR_PRESIDENTIAL_DECISION'] = "(data unavailable)"
            context['MAJOR_INVENTION_OF_YEAR'] = "(data unavailable)"
            context['MAJOR_INVENTION_SUMMARY'] = "(data unavailable)"
    
    async def _gather_generated_facts(self, context: Dict[str, str], year: int, state: str) -> None:
        """Gather OpenAI-generated facts."""
        try:
            # Generate various facts with word limits from define_fields.txt
            facts = await asyncio.gather(
                self.summarizer.generate_fact("", "ww1", 50),
                self.summarizer.generate_fact("", "ww2", 50),
                self.summarizer.generate_fact("", "europe", 50),
                self.summarizer.generate_fact("", "ireland", 50),
                self.summarizer.generate_fact("", "jerusalem", 50),
                self.summarizer.generate_fact("", "india", 50),
                self.summarizer.generate_fact("", "mexico", 50),
                self.summarizer.generate_fact("", "stunt_rigging", 50),
                self.summarizer.generate_fact("", "bike", 100),
                self.summarizer.generate_fact(str(year), "nasa_launch", 100),
                self.summarizer.generate_fact("", "gc", 100),
                self.summarizer.summarize(state, "golf_summary", 150),
                return_exceptions=True
            )
            
            context['WW1_FACT'] = facts[0] if not isinstance(facts[0], Exception) else "(data unavailable)"
            context['WW2_FACT'] = facts[1] if not isinstance(facts[1], Exception) else "(data unavailable)"
            context['EUROPE_FACT'] = facts[2] if not isinstance(facts[2], Exception) else "(data unavailable)"
            context['IRELAND_FACT'] = facts[3] if not isinstance(facts[3], Exception) else "(data unavailable)"
            context['JERUSALEM_FACT'] = facts[4] if not isinstance(facts[4], Exception) else "(data unavailable)"
            context['INDIA_FACT'] = facts[5] if not isinstance(facts[5], Exception) else "(data unavailable)"
            context['MEXICO_FACT'] = facts[6] if not isinstance(facts[6], Exception) else "(data unavailable)"
            context['STUNT_RIGGING_SUMMARY'] = facts[7] if not isinstance(facts[7], Exception) else "(data unavailable)"
            context['BIKE_FUN_FACT'] = facts[8] if not isinstance(facts[8], Exception) else "(data unavailable)"
            context['NASA_LAUNCH_HISTORY'] = facts[9] if not isinstance(facts[9], Exception) else "(data unavailable)"
            context['TEACH_ME_GC'] = facts[10] if not isinstance(facts[10], Exception) else "(data unavailable)"
            context['CURRENT_GOLF_STATE_SUMMARY'] = facts[11] if not isinstance(facts[11], Exception) else "(data unavailable)"
            
            # Get codebase of the day
            try:
                async with CodebaseSelector() as codebase_selector:
                    repo_name, repo_summary = await codebase_selector.get_codebase_of_the_day()
                    context['CODEBASE_TODAY'] = repo_name
                    context['CODEBASE_SUMMARY'] = repo_summary
            except Exception as e:
                logger.error(f"Failed to get codebase: {e}")
                context['CODEBASE_TODAY'] = "(Codebase not available)"
                context['CODEBASE_SUMMARY'] = "(Summary not available)"
            
        except Exception as e:
            logger.error(f"Failed to gather generated facts: {e}")
            context['WW1_FACT'] = "(data unavailable)"
            context['WW2_FACT'] = "(data unavailable)"
            context['EUROPE_FACT'] = "(data unavailable)"
            context['IRELAND_FACT'] = "(data unavailable)"
            context['JERUSALEM_FACT'] = "(data unavailable)"
            context['INDIA_FACT'] = "(data unavailable)"
            context['MEXICO_FACT'] = "(data unavailable)"
            context['STUNT_RIGGING_SUMMARY'] = "(data unavailable)"
            context['BIKE_FUN_FACT'] = "(data unavailable)"
            context['NASA_LAUNCH_HISTORY'] = "(data unavailable)"
            context['TEACH_ME_GC'] = "(data unavailable)"
            context['CURRENT_GOLF_STATE_SUMMARY'] = "(data unavailable)"
            context['CODEBASE_TODAY'] = "(data unavailable)"
            context['CODEBASE_SUMMARY'] = "(data unavailable)"
    
    def _gather_language_section(self, context: Dict[str, str], now: datetime) -> None:
        """Gather daily language section."""
        try:
            # Use day of year to determine which language section to show
            day_of_year = now.timetuple().tm_yday
            
            # Get daily language section
            language_section = self.language_fetcher.get_daily_language_section(day_of_year)
            
            if language_section:
                context['DAILY_LANGUAGE_SECTION'] = self.language_fetcher.format_language_section(language_section)
            else:
                context['DAILY_LANGUAGE_SECTION'] = "(Language section not available)"
                
        except Exception as e:
            logger.error(f"Failed to gather language section: {e}")
            context['DAILY_LANGUAGE_SECTION'] = "(Language section unavailable)"
    
    async def generate_briefing(self, dry_run: bool = False, send_email: bool = False) -> bool:
        """Generate the daily briefing.
        
        Args:
            dry_run: If True, don't send emails
            send_email: If True, send email (ignored if dry_run is True)
            
        Returns:
            True if successful
        """
        try:
            logger.info("Starting daily briefing generation")
            
            # Gather all data
            context = await self.gather_data()
            
            # Render template
            content = self.template_engine.render_template("daily_template.txt", context)
            
            # Write files
            txt_path = self.file_writer.write_daily_txt(content)
            xlsx_path = self.file_writer.update_table_xlsx(context)
            
            logger.info(f"Generated files: {txt_path}, {xlsx_path}")
            
            # Check for missing fields
            missing_fields = self.file_writer.get_missing_fields(context)
            
            if not dry_run and send_email:
                # Send main briefing email
                email_sent = self.emailer.send_daily_brief(content)
                
                if email_sent:
                    logger.info("Daily briefing email sent successfully")
                else:
                    logger.error("Failed to send daily briefing email")
                
                # Send alert email if there are missing fields
                if missing_fields:
                    alert_sent = self.emailer.send_alert_email(missing_fields)
                    if alert_sent:
                        logger.info(f"Alert email sent for {len(missing_fields)} missing fields")
                    else:
                        logger.error("Failed to send alert email")
                        
            elif dry_run:
                logger.info("DRY RUN: Email sending skipped")
                if missing_fields:
                    logger.info(f"Would send alert for missing fields: {missing_fields}")
                print("...EMAIL SENT OK (dry-run)")
                
            return True
            
        except Exception as e:
            logger.error(f"Failed to generate briefing: {e}")
            
            # Send error notification if not dry run
            if not dry_run:
                self.emailer.send_error_notification(
                    "Briefing Generation Error",
                    str(e),
                    {"timestamp": datetime.now().isoformat()}
                )
            
            return False


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Generate daily briefing")
    parser.add_argument("--dry-run", action="store_true", help="Generate files without sending email")
    parser.add_argument("--email", action="store_true", help="Send email after generation")
    
    args = parser.parse_args()
    
    # Create orchestrator
    orchestrator = BriefingOrchestrator()
    
    # Generate briefing
    success = await orchestrator.generate_briefing(
        dry_run=args.dry_run,
        send_email=args.email
    )
    
    if success:
        logger.info("Daily briefing completed successfully")
        return 0
    else:
        logger.error("Daily briefing failed")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
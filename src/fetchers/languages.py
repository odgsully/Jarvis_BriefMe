"""Language fetcher for daily language rotation."""
import csv
from dataclasses import dataclass
from typing import Dict, List, Optional

import pandas as pd

from ..settings import settings
from ..utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class LanguageSection:
    """Represents a language section with translations."""
    section_name: str
    translations: Dict[str, str]


class LanguageFetcher:
    """Fetches language translations with daily rotation."""
    
    def __init__(self):
        """Initialize the language fetcher."""
        self.csv_path = settings.datasets_dir / "Languages.csv"
        self.sections: Optional[List[LanguageSection]] = None
        
    def load_language_sections(self) -> List[LanguageSection]:
        """Load language sections from CSV file.
        
        Returns:
            List of LanguageSection objects
        """
        if self.sections is not None:
            return self.sections
            
        try:
            # Read CSV file
            df = pd.read_csv(self.csv_path)
            
            sections = []
            for _, row in df.iterrows():
                section_name = row['Section']
                translations = {
                    'English': row['English'],
                    'Spanish': row['Spanish'],
                    'French': row['French'],
                    'Japanese': row['Japanese'],
                    'Mandarin': row['Mandarin'],
                    'Italian': row['Italian'],
                    'Arabic': row['Arabic'],
                    'Hebrew': row['Hebrew'],
                    'German': row['German'],
                    'Russian': row['Russian'],
                    'Portuguese': row['Portuguese'],
                }
                
                section = LanguageSection(
                    section_name=section_name,
                    translations=translations
                )
                sections.append(section)
            
            self.sections = sections
            logger.info(f"Loaded {len(sections)} language sections from CSV")
            return sections
            
        except Exception as e:
            logger.error(f"Failed to load language sections from CSV: {e}")
            return []
    
    def get_daily_language_section(self, day_index: int) -> Optional[LanguageSection]:
        """Get the language section for a specific day.
        
        Args:
            day_index: Day index (0-based) to determine which section to return
            
        Returns:
            LanguageSection for the day or None if not found
        """
        sections = self.load_language_sections()
        
        if not sections:
            logger.error("No language sections available")
            return None
        
        # Cycle through sections based on day index
        section_index = day_index % len(sections)
        selected_section = sections[section_index]
        
        logger.info(f"Selected language section '{selected_section.section_name}' for day {day_index}")
        
        return selected_section
    
    def format_language_section(self, section: LanguageSection) -> str:
        """Format a language section for display in the template.
        
        Args:
            section: LanguageSection to format
            
        Returns:
            Formatted string for template display
        """
        if not section:
            return ""
            
        lines = [f"{section.section_name}."]
        
        # Add each language translation
        for lang, translation in section.translations.items():
            lines.append(f"{lang} — {translation}")
        
        return "\n".join(lines)
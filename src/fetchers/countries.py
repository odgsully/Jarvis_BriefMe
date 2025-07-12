"""Countries fetcher using local CSV data."""
import csv
import random
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

import pandas as pd

from ..generators.summariser import Summarizer
from ..settings import settings
from ..utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class Country:
    """Represents country information."""
    name: str
    capital: str
    region: str
    subregion: str
    population: int
    area: float
    languages: List[str]
    currencies: List[str]
    lat: float
    lng: float
    
    def get_location_description(self) -> str:
        """Get a description of the capital's location.
        
        Returns:
            Location description for someone unfamiliar with the geography
        """
        # Build description based on region and subregion
        desc_parts = [f"{self.capital} is the capital city of {self.name}"]
        
        if self.subregion:
            desc_parts.append(f"located in {self.subregion}")
        elif self.region:
            desc_parts.append(f"located in {self.region}")
            
        # Add relative position
        if self.lat > 0:
            hemisphere = "Northern Hemisphere"
        else:
            hemisphere = "Southern Hemisphere"
            
        desc_parts.append(f"in the {hemisphere}")
        
        # Add continent context
        continent_context = {
            "Africa": "on the African continent",
            "Americas": "in the Americas",
            "Asia": "on the Asian continent",
            "Europe": "on the European continent",
            "Oceania": "in the Oceania region",
        }
        
        if self.region in continent_context:
            desc_parts.append(continent_context[self.region])
            
        return f"{', '.join(desc_parts)}."


class CountriesFetcher:
    """Fetches country data from local CSV file."""
    
    def __init__(self):
        """Initialize the countries fetcher."""
        self.csv_path = settings.datasets_dir / "Countries.csv"
        self.countries: Optional[List[Country]] = None
        self.summarizer = Summarizer()
        
    async def __aenter__(self):
        """Async context manager entry."""
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        pass
    
    def load_countries(self) -> List[Country]:
        """Load countries from CSV file.
        
        Returns:
            List of Country objects
        """
        if self.countries is not None:
            return self.countries
            
        try:
            # Read CSV file
            df = pd.read_csv(self.csv_path)
            
            countries = []
            for _, row in df.iterrows():
                # Parse languages and currencies
                languages = row.get('Languages', '').split('|') if pd.notna(row.get('Languages')) else []
                currencies = row.get('Currencies', '').split('|') if pd.notna(row.get('Currencies')) else []
                
                country = Country(
                    name=row['Country'],
                    capital=row['Capital'],
                    region=row.get('Region', ''),
                    subregion=row.get('Subregion', ''),
                    population=int(row.get('Population', 0)),
                    area=float(row.get('Area', 0)),
                    languages=[lang.strip() for lang in languages],
                    currencies=[curr.strip() for curr in currencies],
                    lat=float(row.get('Latitude', 0)),
                    lng=float(row.get('Longitude', 0)),
                )
                countries.append(country)
            
            self.countries = countries
            logger.info(f"Loaded {len(countries)} countries from CSV")
            return countries
            
        except Exception as e:
            logger.error(f"Failed to load countries from CSV: {e}")
            return []
    
    async def get_random_country(self) -> Optional[Tuple[Country, str]]:
        """Get a random country with its location description.
        
        Returns:
            Tuple of (Country, location_description) or None
        """
        countries = self.load_countries()
        
        if not countries:
            logger.error("No countries available")
            return None
            
        # Select random country
        country = random.choice(countries)
        
        # Generate enhanced location description using GPT
        location_prompt = f"Describe the location of {country.capital}, the capital of {country.name}, as if explaining to someone totally unfamiliar with its geography. Include its position relative to the country, nearby major cities or landmarks, geographic features (mountains, rivers, coasts), and climate characteristics."
        
        try:
            enhanced_location = await self.summarizer.summarize(
                f"{country.capital}, {country.name}",
                "fact",
                100,
                location_prompt
            )
        except Exception as e:
            logger.warning(f"Failed to generate enhanced location: {e}")
            enhanced_location = country.get_location_description()
        
        logger.info(f"Selected random country: {country.name}")
        
        return country, enhanced_location
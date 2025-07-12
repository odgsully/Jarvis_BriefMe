"""REST Countries API fetcher for random country selection."""
import random
from dataclasses import dataclass
from typing import List, Optional, Tuple

import httpx

from ..utils.logger import get_logger
from ..utils.retry import async_retry

logger = get_logger(__name__)

REST_COUNTRIES_API = "https://restcountries.com/v3.1"


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


class RestCountriesFetcher:
    """Fetches country data from REST Countries API."""
    
    def __init__(self):
        """Initialize the countries fetcher."""
        self.client = httpx.AsyncClient(timeout=30.0)
        self._countries_cache: Optional[List[Country]] = None
        
    async def __aenter__(self):
        """Async context manager entry."""
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.client.aclose()
    
    @async_retry(max_attempts=3, initial_delay=1.0)
    async def fetch_all_countries(self) -> List[Country]:
        """Fetch all countries from the API.
        
        Returns:
            List of all countries
        """
        if self._countries_cache is not None:
            return self._countries_cache
            
        url = f"{REST_COUNTRIES_API}/all"
        
        try:
            response = await self.client.get(url)
            response.raise_for_status()
            
            data = response.json()
            countries = []
            
            for country_data in data:
                try:
                    # Extract country information
                    name = country_data.get("name", {}).get("common", "")
                    
                    # Get capital (some countries have multiple)
                    capitals = country_data.get("capital", [])
                    capital = capitals[0] if capitals else "No capital"
                    
                    # Get region info
                    region = country_data.get("region", "")
                    subregion = country_data.get("subregion", "")
                    
                    # Get population and area
                    population = country_data.get("population", 0)
                    area = country_data.get("area", 0.0)
                    
                    # Get languages
                    languages_dict = country_data.get("languages", {})
                    languages = list(languages_dict.values())
                    
                    # Get currencies
                    currencies_dict = country_data.get("currencies", {})
                    currencies = [curr.get("name", "") for curr in currencies_dict.values()]
                    
                    # Get coordinates
                    latlng = country_data.get("latlng", [0, 0])
                    lat = latlng[0] if len(latlng) > 0 else 0
                    lng = latlng[1] if len(latlng) > 1 else 0
                    
                    # Skip if no name or capital
                    if not name or not capital or capital == "No capital":
                        continue
                        
                    country = Country(
                        name=name,
                        capital=capital,
                        region=region,
                        subregion=subregion,
                        population=population,
                        area=area,
                        languages=languages,
                        currencies=currencies,
                        lat=lat,
                        lng=lng,
                    )
                    
                    countries.append(country)
                    
                except Exception as e:
                    logger.warning(f"Failed to parse country data: {e}")
                    continue
            
            self._countries_cache = countries
            logger.info(f"Fetched {len(countries)} countries")
            
            return countries
            
        except Exception as e:
            logger.error(f"Failed to fetch countries: {e}")
            return []
    
    async def get_random_country(self) -> Optional[Tuple[Country, str]]:
        """Get a random country with its location description.
        
        Returns:
            Tuple of (Country, location_description) or None
        """
        countries = await self.fetch_all_countries()
        
        if not countries:
            logger.error("No countries available")
            return None
            
        # Select random country
        country = random.choice(countries)
        
        # Generate location description
        location_desc = country.get_location_description()
        
        logger.info(f"Selected random country: {country.name}")
        
        return country, location_desc
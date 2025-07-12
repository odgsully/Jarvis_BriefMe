"""Cycle engine for managing DaysLeft, Year, and State progression."""
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Tuple

from ..settings import settings
from ..utils.logger import get_logger

logger = get_logger(__name__)

# US States in alphabetical order
US_STATES = [
    "Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado",
    "Connecticut", "Delaware", "Florida", "Georgia", "Hawaii", "Idaho",
    "Illinois", "Indiana", "Iowa", "Kansas", "Kentucky", "Louisiana",
    "Maine", "Maryland", "Massachusetts", "Michigan", "Minnesota",
    "Mississippi", "Missouri", "Montana", "Nebraska", "Nevada",
    "New Hampshire", "New Jersey", "New Mexico", "New York",
    "North Carolina", "North Dakota", "Ohio", "Oklahoma", "Oregon",
    "Pennsylvania", "Rhode Island", "South Carolina", "South Dakota",
    "Tennessee", "Texas", "Utah", "Vermont", "Virginia", "Washington",
    "West Virginia", "Wisconsin", "Wyoming"
]


@dataclass
class CycleState:
    """Represents the current cycle state."""
    year: int
    state_index: int
    days_left: int
    last_updated: str
    
    @property
    def current_state(self) -> str:
        """Get the current US state name."""
        return US_STATES[self.state_index % len(US_STATES)]


class CycleEngine:
    """Manages the 3-day cycle for year and state progression."""
    
    def __init__(self, state_file: str = "cycles.json"):
        """Initialize the cycle engine.
        
        Args:
            state_file: Name of the JSON file to store state
        """
        self.state_file = settings.root_dir / state_file
        self.state = self._load_state()
        
    def _load_state(self) -> CycleState:
        """Load state from JSON file or create initial state.
        
        Returns:
            Current cycle state
        """
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    data = json.load(f)
                    
                state = CycleState(**data)
                logger.info(
                    "Loaded cycle state",
                    year=state.year,
                    state=state.current_state,
                    days_left=state.days_left,
                )
                return state
                
            except Exception as e:
                logger.error(f"Failed to load cycle state: {e}")
                # Fall through to create new state
        
        # Create initial state
        initial_state = CycleState(
            year=1980,
            state_index=0,
            days_left=3,
            last_updated=datetime.now().isoformat(),
        )
        
        logger.info("Created initial cycle state")
        self._save_state(initial_state)
        return initial_state
    
    def _save_state(self, state: CycleState) -> None:
        """Save state to JSON file.
        
        Args:
            state: Cycle state to save
        """
        try:
            with open(self.state_file, 'w') as f:
                json.dump(asdict(state), f, indent=2)
                
            logger.info("Saved cycle state")
            
        except Exception as e:
            logger.error(f"Failed to save cycle state: {e}")
            raise
    
    def advance(self) -> Tuple[int, str, int]:
        """Advance the cycle by one day.
        
        Returns:
            Tuple of (current_year, current_state, days_left)
        """
        # Check if we need to advance (different day)
        last_date = datetime.fromisoformat(self.state.last_updated).date()
        current_date = datetime.now().date()
        
        if last_date >= current_date:
            # Same day, return current values
            logger.info("Same day, returning current cycle values")
            return self.state.year, self.state.current_state, self.state.days_left
        
        # Advance the cycle
        if self.state.days_left > 1:
            # Just decrement days_left
            self.state.days_left -= 1
            logger.info(f"Decremented days_left to {self.state.days_left}")
        else:
            # Reset days_left and advance year/state
            self.state.days_left = 3
            self.state.year += 1
            self.state.state_index += 1
            
            # Wrap state index if needed
            if self.state.state_index >= len(US_STATES):
                self.state.state_index = 0
                
            logger.info(
                "Reset cycle",
                new_year=self.state.year,
                new_state=self.state.current_state,
                days_left=self.state.days_left,
            )
        
        # Update timestamp
        self.state.last_updated = datetime.now().isoformat()
        
        # Save state
        self._save_state(self.state)
        
        return self.state.year, self.state.current_state, self.state.days_left
    
    def get_current(self) -> Tuple[int, str, int]:
        """Get current cycle values without advancing.
        
        Returns:
            Tuple of (current_year, current_state, days_left)
        """
        return self.state.year, self.state.current_state, self.state.days_left
    
    def reset(self, year: int = 1980, state_index: int = 0, days_left: int = 3) -> None:
        """Reset the cycle to specific values.
        
        Args:
            year: Starting year
            state_index: Starting state index
            days_left: Starting days left
        """
        self.state = CycleState(
            year=year,
            state_index=state_index,
            days_left=days_left,
            last_updated=datetime.now().isoformat(),
        )
        
        self._save_state(self.state)
        logger.info(
            "Reset cycle state",
            year=year,
            state=self.state.current_state,
            days_left=days_left,
        )
    
    def simulate_days(self, num_days: int) -> List[Tuple[int, str, int]]:
        """Simulate advancing the cycle for multiple days.
        
        Args:
            num_days: Number of days to simulate
            
        Returns:
            List of (year, state, days_left) tuples for each day
        """
        results = []
        
        # Save current state
        original_state = CycleState(
            year=self.state.year,
            state_index=self.state.state_index,
            days_left=self.state.days_left,
            last_updated=self.state.last_updated,
        )
        
        for i in range(num_days):
            # Force advance by setting last_updated to yesterday
            yesterday = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            yesterday = yesterday.replace(day=yesterday.day - 1)
            self.state.last_updated = yesterday.isoformat()
            
            year, state, days = self.advance()
            results.append((year, state, days))
        
        # Restore original state
        self.state = original_state
        self._save_state(self.state)
        
        return results
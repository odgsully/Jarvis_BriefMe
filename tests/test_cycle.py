"""Tests for the cycle engine."""
import json
import tempfile
from pathlib import Path

import pytest

from src.generators.cycle import CycleEngine, CycleState, US_STATES


class TestCycleEngine:
    """Test the cycle engine functionality."""
    
    @pytest.fixture
    def temp_state_file(self):
        """Create a temporary state file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = Path(f.name)
        yield temp_path
        temp_path.unlink(missing_ok=True)
    
    @pytest.fixture
    def cycle_engine(self, temp_state_file):
        """Create a cycle engine with a temporary state file."""
        return CycleEngine(state_file=str(temp_state_file.name))
    
    def test_initial_state(self, cycle_engine):
        """Test initial state creation."""
        year, state, days_left = cycle_engine.get_current()
        
        assert year == 1980
        assert state == "Alabama"
        assert days_left == 3
    
    def test_10_day_cycle(self, cycle_engine):
        """Test 10 successive days produce correct 3-2-1 cycle and year/state rollover."""
        expected_patterns = [
            (1980, "Alabama", 3),    # Day 1 (initial)
            (1980, "Alabama", 2),    # Day 2
            (1980, "Alabama", 1),    # Day 3
            (1981, "Alaska", 3),     # Day 4 (rollover)
            (1981, "Alaska", 2),     # Day 5
            (1981, "Alaska", 1),     # Day 6
            (1982, "Arizona", 3),    # Day 7 (rollover)
            (1982, "Arizona", 2),    # Day 8
            (1982, "Arizona", 1),    # Day 9
            (1983, "Arkansas", 3),   # Day 10 (rollover)
        ]
        
        # Get initial state
        results = [cycle_engine.get_current()]
        
        # Simulate 9 more days
        simulated = cycle_engine.simulate_days(9)
        results.extend(simulated)
        
        # Verify each day matches expected pattern
        for i, (expected, actual) in enumerate(zip(expected_patterns, results)):
            assert actual == expected, f"Day {i+1}: Expected {expected}, got {actual}"
    
    def test_state_wraparound(self, cycle_engine):
        """Test that states wrap around after reaching Wyoming."""
        # Set to last state
        cycle_engine.reset(year=2000, state_index=len(US_STATES) - 1, days_left=1)
        
        # Verify we're at Wyoming
        year, state, days_left = cycle_engine.get_current()
        assert state == "Wyoming"
        assert days_left == 1
        
        # Simulate one day to trigger rollover
        results = cycle_engine.simulate_days(1)
        year, state, days_left = results[0]
        
        assert year == 2001
        assert state == "Alabama"  # Should wrap back to first state
        assert days_left == 3
    
    def test_persistence(self, temp_state_file):
        """Test that state persists across instances."""
        # Create first engine and advance
        engine1 = CycleEngine(state_file=str(temp_state_file.name))
        engine1.reset(year=1985, state_index=5, days_left=2)
        
        # Create second engine with same file
        engine2 = CycleEngine(state_file=str(temp_state_file.name))
        year, state, days_left = engine2.get_current()
        
        assert year == 1985
        assert state == US_STATES[5]
        assert days_left == 2
    
    def test_same_day_no_advance(self, cycle_engine):
        """Test that calling advance multiple times on same day doesn't change state."""
        # Get initial state
        initial = cycle_engine.get_current()
        
        # Try to advance multiple times (should return same values)
        result1 = cycle_engine.advance()
        result2 = cycle_engine.advance()
        result3 = cycle_engine.advance()
        
        assert result1 == initial
        assert result2 == initial
        assert result3 == initial
    
    def test_reset_functionality(self, cycle_engine):
        """Test reset functionality."""
        # Reset to specific values
        cycle_engine.reset(year=2020, state_index=10, days_left=1)
        
        year, state, days_left = cycle_engine.get_current()
        assert year == 2020
        assert state == US_STATES[10]
        assert days_left == 1
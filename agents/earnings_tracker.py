"""
Earnings Tracker Agent
Maintains a local ledger of bounties won and total USD earned.
"""

import json
import os
import logging
from typing import Callable, Any

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class EarningsTracker:
    """
    Agent responsible for calculating Return on Investment (ROI) and total earnings.
    """
    
    def __init__(self, publish_event: Callable[[Any], None]):
        """
        Initialize the EarningsTracker.
        
        Args:
            publish_event: Callback function to emit events.
        """
        self.publish_event = publish_event
        self.earnings_file = os.path.join(os.getcwd(), "earnings.json")

    def calculate_roi(self, payload: dict):
        """
        Updates the local ledger with new earnings.
        
        Args:
            payload: Dictionary containing PR details.
        """
        logger.info("EarningsTracker: Recalculating ROI...")
        
        earnings = {"total_usd": 0.0, "bounties_won": 0}
        if os.path.exists(self.earnings_file):
            try:
                with open(self.earnings_file, "r") as f:
                    earnings = json.load(f)
            except Exception as e:
                logger.warning(f"EarningsTracker: Could not read existing earnings file: {e}")
                
        # Simulate a bounty win (e.g. $50)
        earnings["total_usd"] += 50.0
        earnings["bounties_won"] += 1
        
        try:
            with open(self.earnings_file, "w") as f:
                json.dump(earnings, f, indent=4)
            logger.info(f"EarningsTracker: Current Total Earnings: ${earnings['total_usd']}")
        except Exception as e:
            logger.error(f"EarningsTracker: Failed to update earnings: {e}")

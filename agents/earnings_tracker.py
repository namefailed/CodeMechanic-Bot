"""
Earnings Tracker Agent
Maintains a local ledger of bounties won and total USD earned.
"""

import json
import os
import logging
from typing import Callable, Any
from utils.database import Database

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
        self.db = Database()

    def calculate_roi(self, payload: dict):
        """
        Recomputes the earnings ledger from confirmed payouts in the database.

        Earnings reflect only bounties whose PRs were actually merged
        (status PAYOUT_CONFIRMED), not every submission — so this no longer
        invents a flat amount per PR.
        """
        logger.info("EarningsTracker: Recalculating ROI from confirmed payouts...")

        summary = self.db.get_earnings_summary()
        earnings = {
            "total_usd": round(summary["total_earned"], 2),
            "bounties_won": summary["bounties_won"],
        }

        try:
            with open(self.earnings_file, "w") as f:
                json.dump(earnings, f, indent=4)
            logger.info(f"EarningsTracker: Confirmed earnings: {earnings['total_usd']} across {earnings['bounties_won']} bounties.")
        except Exception as e:
            logger.error(f"EarningsTracker: Failed to update earnings: {e}")

"""
Orchestrator
The central brain of bug-bot.
Initializes the EventBus and all Agents. Maps events to their respective agent handlers.
Runs the continuous scanning loop.
"""

import time
import yaml
import logging
from typing import Callable, Dict, List
from events import BaseEvent

from agents.bounty_radar import BountyRadar
from agents.scam_detector import ScamDetector
from agents.pr_engineer import PREngineer
from agents.code_reviewer import CodeReviewer
from agents.content_engine import ContentEngine
from agents.devops_monitor import DevOpsMonitor
from agents.earnings_tracker import EarningsTracker
from agents.review_tracker import ReviewTracker

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class EventBus:
    """
    A simple publish-subscribe event bus to decouple agents.
    """
    def __init__(self):
        self.subscribers: Dict[str, List[Callable]] = {}

    def subscribe(self, event_type: str, callback: Callable):
        """Register a callback for a specific event type."""
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append(callback)

    def publish(self, event: BaseEvent):
        """Emit an event to all registered subscribers."""
        logger.info(f"[EventBus] Emitting: {event.event_type}")
        if event.event_type in self.subscribers:
            for callback in self.subscribers[event.event_type]:
                try:
                    callback(event.payload)
                except Exception as e:
                    logger.error(f"[EventBus] Error in callback {callback.__name__} for event {event.event_type}: {e}")

class Orchestrator:
    """
    Main controller for the bug-bot pipeline.
    """
    def __init__(self, config_path: str = "config.yaml"):
        self.bus = EventBus()
        self.load_config(config_path)
        self.init_agents()
        self.setup_subscriptions()

    def load_config(self, config_path: str):
        """Loads configuration settings from a YAML file."""
        try:
            with open(config_path, "r") as f:
                self.config = yaml.safe_load(f)
            logger.info("Config loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            self.config = {}

    def init_agents(self):
        """Instantiates all agents and injects the publish method."""
        self.radar = BountyRadar(self.bus.publish)
        self.scam_detector = ScamDetector(self.bus.publish)
        self.pr_engineer = PREngineer(self.bus.publish)
        self.reviewer = CodeReviewer(self.bus.publish)
        self.content_engine = ContentEngine(self.bus.publish)
        self.devops_monitor = DevOpsMonitor(self.bus.publish)
        self.earnings_tracker = EarningsTracker(self.bus.publish)
        self.review_tracker = ReviewTracker(self.bus.publish)

    def setup_subscriptions(self):
        """Wires up the event pipeline between agents."""
        self.bus.subscribe("BOUNTY_FOUND", self.scam_detector.evaluate)
        self.bus.subscribe("BOUNTY_VERIFIED", self.pr_engineer.solve_issue)
        self.bus.subscribe("PR_READY", self.reviewer.review)
        self.bus.subscribe("PR_SUBMITTED", self.content_engine.draft_post)
        self.bus.subscribe("PR_SUBMITTED", self.devops_monitor.track_ci)
        self.bus.subscribe("PR_SUBMITTED", self.earnings_tracker.calculate_roi)
        self.bus.subscribe("PR_REVIEWED", self.pr_engineer.solve_issue)

    def run(self):
        """Starts the infinite scanning loop."""
        logger.info("Starting bug-bot Orchestrator loop...")
        try:
            while True:
                logger.info("--- Starting new scan cycle ---")
                self.radar.scan()
                self.review_tracker.track()
                logger.info("--- Scan cycle complete. Sleeping for 30 minutes ---")
                time.sleep(1800) # Scan every 30 mins
        except KeyboardInterrupt:
            logger.info("\nShutting down Orchestrator gracefully.")
        except Exception as e:
            logger.error(f"Orchestrator encountered a fatal error: {e}")

if __name__ == "__main__":
    orchestrator = Orchestrator()
    orchestrator.run()

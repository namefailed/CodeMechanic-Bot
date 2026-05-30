from orchestrator import Orchestrator

def test():
    print("Testing Bounty Funnel...")
    # Initialize the orchestrator (this sets up the event bus and agents)
    bot = Orchestrator()
    
    # Trigger a single scan
    bot.radar.scan()

if __name__ == "__main__":
    test()

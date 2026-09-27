import sys, os
# Add project root to PYTHONPATH
project_root = r"c:/Users/Dell 7420/Desktop/antigravity/codeatlas"
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Now import and run the test script
import asyncio
from scratch.test_all_queries import run_queries

if __name__ == "__main__":
    asyncio.run(run_queries())

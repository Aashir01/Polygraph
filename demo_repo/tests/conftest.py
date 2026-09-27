"""demo_repo test configuration."""
import sys
from pathlib import Path

# Make the `shop` package importable when pytest is run from demo_repo/
sys.path.insert(0, str(Path(__file__).parent.parent))

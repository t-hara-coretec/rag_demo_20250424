# Make rag_utils importable as a package
from pathlib import Path
import sys

# Add the current directory to sys.path if not already there
_current_dir = Path(__file__).parent
if str(_current_dir) not in sys.path:
    sys.path.insert(0, str(_current_dir))
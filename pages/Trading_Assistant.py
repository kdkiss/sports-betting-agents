import runpy
from pathlib import Path
import sys

script_path = Path(__file__).parents[1] / "trading_assistant.py"
sys.path.insert(0, str(script_path.parent))
runpy.run_path(script_path, run_name="__main__")

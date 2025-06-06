import runpy
from pathlib import Path
import sys

script_dir = Path(__file__).parents[1] / "sports-betting-agent"
sys.path.insert(0, str(script_dir))
script_path = script_dir / "app.py"
runpy.run_path(script_path, run_name="__main__")

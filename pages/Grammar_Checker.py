import runpy
from pathlib import Path
import sys

script_path = Path(__file__).parents[1] / "grammar_checker_2.py"
sys.path.insert(0, str(script_path.parent))
runpy.run_path(script_path, run_name="__main__")

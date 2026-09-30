"""Entry point for `python -m baxters_power_goo`."""

import runpy
import pathlib

_root = pathlib.Path(__file__).parent.parent.parent
runpy.run_path(str(_root / "main.py"), run_name="__main__")

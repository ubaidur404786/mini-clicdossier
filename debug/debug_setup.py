import sys
from pathlib import Path 

import pymupdf
import src

ROOT =Path.cwd()

python_path=sys.executable
in_venv=".venv" in python_path
src_folder=Path(src.__file__).parent
data_folder=ROOT/"data"

print("python:", python_path)
print("in venv:", in_venv)
print("cwd:", ROOT)
print("src package:", src_folder)
print("data folder exists:", data_folder.exists())
print("pymupdf version:", pymupdf.__version__)
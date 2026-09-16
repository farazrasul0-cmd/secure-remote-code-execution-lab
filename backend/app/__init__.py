"""Backend application package for Secure Real-Time Remote Code Execution Lab."""

import sys
from pathlib import Path

# Ensure project root is in sys.path so worker modules are importable
_project_root = str(Path(__file__).resolve().parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

__version__ = "0.1.0"

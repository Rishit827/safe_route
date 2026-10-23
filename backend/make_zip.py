"""Rebuild the SafeRoute project ZIP from the source files in this folder."""
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parent
OUT = ROOT.parent / "saferoute-backend.zip"
with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as archive:
    for path in ROOT.rglob("*"):
        if path.is_file() and path.name != "__pycache__":
            archive.write(path, path.relative_to(ROOT.parent))
print(f"Created {OUT}")

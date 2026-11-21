"""Load the exact reviewed, unmodified Tablib wheel without installing packages."""
from hashlib import sha256
from pathlib import Path
import sys

WHEEL = Path(__file__).resolve().parent / "vendor" / "tablib-3.10.0-py3-none-any.whl"
WHEEL_SHA256 = "5721bf3a52d491f8f843628a3a3200db164f6ad9e92fb6eaa64dc3f945f30ad9"
if sha256(WHEEL.read_bytes()).hexdigest() != WHEEL_SHA256:
    raise RuntimeError("TABLIB_WHEEL_HASH_MISMATCH")
if "tablib" in sys.modules:
    raise RuntimeError("TABLIB_ALREADY_IMPORTED_USE_FRESH_PROCESS")
sys.path.insert(0, str(WHEEL))
import tablib  # noqa: E402
if not str(tablib.__file__).startswith(str(WHEEL)):
    raise RuntimeError("TABLIB_ORIGIN_MISMATCH")

# Imports explicitly initialize the pinned 3.10 registry on Python 3.15 as well.
from tablib.formats._html import HTMLFormat  # noqa: E402
from xml.etree import ElementTree as ET  # noqa: E402


class FormattedHTML:
    """Apply the same cell formatters as CSV before rendering an HTML copy.

    Opt-in adapter, no global registry patch. It uses Tablib's pinned _package
    method, so formatter order and all-column formatters match CSV behavior.
    Formatter callbacks themselves must be trusted application code.
    """
    @staticmethod
    def export_set(dataset):
        rows = dataset._package(dicts=False)
        if dataset.headers:
            formatted = tablib.Dataset(*rows[1:], headers=rows[0])
        else:
            formatted = tablib.Dataset(*rows)
        return HTMLFormat.export_set(formatted)

    @classmethod
    def export_book(cls, databook):
        pieces = []
        for i, dataset in enumerate(databook.sheets()):
            title = ET.Element("h3")
            title.text = str(dataset.title) if dataset.title else f"Set {i}"
            pieces.extend([ET.tostring(title, method="html", encoding="unicode"),
                           cls.export_set(dataset)])
        return "\n".join(pieces)

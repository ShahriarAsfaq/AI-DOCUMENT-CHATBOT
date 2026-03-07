from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class Document:
    """Simple document container used throughout the RAG subsystem.

    Attributes:
        page_content: textual content of the document/chunk
        metadata: arbitrary dictionary of metadata (e.g. source, page number)
    """

    page_content: str
    metadata: Dict[str, Any]

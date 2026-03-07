"""Document loader for PDF and DOCX files.

Supports extracting text from PDF and DOCX documents with metadata. Uses
an internal Document dataclass so there is no external dependency.
"""

import os
from pathlib import Path
from typing import List

from pypdf import PdfReader
from docx import Document as DocxDocument

from .document import Document


def load_document(file_path: str) -> List[Document]:
    """Load and extract text from PDF or DOCX files.

    Args:
        file_path: Path to the PDF or DOCX file.

    Returns:
        List of Document objects with extracted text and metadata.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file format is not supported (not PDF or DOCX).
        Exception: For other document processing errors.
    """
    file_path = Path(file_path)

    # Validate file exists
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    # Get file extension and name
    file_ext = file_path.suffix.lower()
    file_name = file_path.name

    # Route to appropriate loader
    if file_ext == ".pdf":
        return _load_pdf(file_path, file_name)
    elif file_ext == ".docx":
        return _load_docx(file_path, file_name)
    else:
        raise ValueError(
            f"Unsupported file format: {file_ext}. Supported formats: .pdf, .docx"
        )


def _load_pdf(file_path: Path, file_name: str) -> List[Document]:
    """Extract text from PDF file.

    Args:
        file_path: Path to the PDF file.
        file_name: Name of the file for metadata.

    Returns:
        List of Document objects, one per page.

    Raises:
        Exception: If PDF processing fails.
    """
    documents: List[Document] = []

    try:
        pdf_reader = PdfReader(str(file_path))
        num_pages = len(pdf_reader.pages)

        for page_num in range(num_pages):
            page = pdf_reader.pages[page_num]
            text = page.extract_text() or ""

            if text.strip():  # Only add non-empty pages
                documents.append(
                    Document(
                        page_content=text,
                        metadata={
                            "page": page_num + 1,  # 1-indexed
                            "source": file_name,
                        },
                    )
                )

        if not documents:
            raise ValueError(f"No text content found in PDF: {file_name}")

        return documents

    except Exception as e:
        raise Exception(f"Error processing PDF '{file_name}': {str(e)}") from e


def _load_docx(file_path: Path, file_name: str) -> List[Document]:
    """Extract text from DOCX file.

    Args:
        file_path: Path to the DOCX file.
        file_name: Name of the file for metadata.

    Returns:
        List of Document objects. For DOCX, typically one document with all content.

    Raises:
        Exception: If DOCX processing fails.
    """
    documents = []

    try:
        docx = DocxDocument(str(file_path))
        text_content = []

        # Extract text from all paragraphs
        for para in docx.paragraphs:
            if para.text.strip():
                text_content.append(para.text)

        full_text = "\n".join(text_content)

        if not full_text.strip():
            raise ValueError(f"No text content found in DOCX: {file_name}")

        # Create single document for DOCX (page concept doesn't apply)
        doc = Document(
            page_content=full_text,
            metadata={
                "page": 1,  # DOCX treated as single document
                "source": file_name,
            },
        )
        documents.append(doc)

        return documents

    except Exception as e:
        raise Exception(f"Error processing DOCX '{file_name}': {str(e)}") from e

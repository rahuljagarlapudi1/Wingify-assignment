
import re
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path
import PyPDF2
import pdfplumber
import fitz  # PyMuPDF
from docx import Document as DocxDocument
from pydantic import BaseModel, Field

from langchain_core.tools import StructuredTool
from config.settings import settings

logger = logging.getLogger(__name__)

class ParseDocInput(BaseModel):
    path: str = Field(..., description="Path to the document (.pdf/.docx/.txt)")
    doc_type: Optional[str] = Field(None, description="Optional: e.g., '10-Q', '10-K', 'investor update'")

class ExtractMetricsInput(BaseModel):
    text: str = Field(..., description="Raw document text to analyze for metrics")

class FinancialDocumentTool:
    """Enhanced financial document processing with multiple extractors."""

    @staticmethod
    def read_document(file_path: str) -> str:
        """Extract text from financial documents with fallback methods."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Document not found: {file_path}")

        if path.stat().st_size > settings.MAX_FILE_SIZE:
            raise ValueError(f"File too large: {path.stat().st_size} bytes")

        ext = path.suffix.lower()

        try:
            if ext == ".pdf":
                return FinancialDocumentTool._extract_pdf(file_path)
            elif ext == ".docx":
                return FinancialDocumentTool._extract_docx(file_path)
            elif ext == ".txt":
                return FinancialDocumentTool._extract_txt(file_path)
            else:
                raise ValueError(f"Unsupported file type: {ext}")
        except Exception as e:
            logger.error(f"Document extraction failed for {file_path}: {e}")
            raise

    @staticmethod
    def _extract_pdf(file_path: str) -> str:
        """Extract PDF text with multiple fallback methods."""
        extractors = [
            FinancialDocumentTool._extract_with_pdfplumber,
            FinancialDocumentTool._extract_with_pymupdf,
            FinancialDocumentTool._extract_with_pypdf2,
        ]

        for extractor in extractors:
            try:
                text = extractor(file_path)
                if len(text.strip()) > 50:  # Minimum viable content
                    return FinancialDocumentTool._clean_financial_text(text)
            except Exception as e:
                logger.debug(f"{extractor.__name__} failed: {e}")
                continue

        raise RuntimeError(f"All PDF extractors failed for: {file_path}")

    @staticmethod
    def _extract_with_pdfplumber(file_path: str) -> str:
        """Extract using pdfplumber with table support."""
        full_text = ""
        try:
            with pdfplumber.open(file_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    # Extract text
                    text = page.extract_text() or ""
                    full_text += f"\n[Page {page_num + 1}]\n{text}\n"

                    # Extract tables
                    try:
                        tables = page.extract_tables() or []
                        if tables:
                            for table_num, table in enumerate(tables):
                                table_text = FinancialDocumentTool._format_table_text(table)
                                full_text += f"\n[Table {table_num + 1}]\n{table_text}\n"
                    except Exception as e:
                        logger.debug(f"Table extraction failed on page {page_num}: {e}")
        except Exception as e:
            logger.error(f"pdfplumber extraction failed: {e}")
            raise
        return full_text

    @staticmethod
    def _extract_with_pymupdf(file_path: str) -> str:
        """Extract using PyMuPDF."""
        full_text = ""
        try:
            doc = fitz.open(file_path)
            try:
                for page_num in range(doc.page_count):
                    page = doc[page_num]
                    text = page.get_text()
                    full_text += f"\n[Page {page_num + 1}]\n{text}\n"
            finally:
                doc.close()
        except Exception as e:
            logger.error(f"PyMuPDF extraction failed: {e}")
            raise
        return full_text

    @staticmethod
    def _extract_with_pypdf2(file_path: str) -> str:
        """Extract using PyPDF2."""
        full_text = ""
        try:
            with open(file_path, "rb") as file:
                reader = PyPDF2.PdfReader(file)
                for page_num, page in enumerate(reader.pages):
                    text = page.extract_text() or ""
                    full_text += f"\n[Page {page_num + 1}]\n{text}\n"
        except Exception as e:
            logger.error(f"PyPDF2 extraction failed: {e}")
            raise
        return full_text

    @staticmethod
    def _extract_docx(file_path: str) -> str:
        """Extract DOCX content."""
        try:
            doc = DocxDocument(file_path)
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            text = "\n".join(paragraphs)
            return FinancialDocumentTool._clean_financial_text(text)
        except Exception as e:
            logger.error(f"DOCX extraction failed: {e}")
            raise

    @staticmethod
    def _extract_txt(file_path: str) -> str:
        """Extract plain text."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
                text = file.read()
            return FinancialDocumentTool._clean_financial_text(text)
        except Exception as e:
            logger.error(f"TXT extraction failed: {e}")
            raise

    @staticmethod
    def _format_table_text(table: List[List[str]]) -> str:
        """Format table data as text."""
        if not table:
            return ""
        formatted_rows = []
        for row in table:
            if row:
                cells = [str(cell).strip() if cell else "" for cell in row]
                formatted_rows.append(" | ".join(cells))
        return "\n".join(formatted_rows)

    @staticmethod
    def _clean_financial_text(text: str) -> str:
        """Clean and normalize financial document text."""
        if not text:
            return ""
        text = re.sub(r'\r\n?', '\n', text)               # Normalize line endings
        text = re.sub(r'[ \t]+', ' ', text)               # Collapse spaces/tabs
        text = re.sub(r'\n\s*\n\s*\n', '\n\n', text)      # Limit blank lines
        text = re.sub(r'\$\s+', '$', text)                # Fix $ formatting
        text = re.sub(r'(\d)\s+,\s*(\d)', r'\1,\2', text) # Fix spaced commas
        text = re.sub(r'Page \d+ of \d+', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\n\s*\n', '\n\n', text)
        return text.strip()

    @staticmethod
    def extract_financial_metrics(text: str) -> Dict[str, Any]:
        """Extract key financial metrics from text."""
        metrics: Dict[str, Any] = {}
        if not text:
            return metrics

        def extract_values(patterns: List[str], key: str) -> None:
            for pattern in patterns:
                matches = re.findall(pattern, text, flags=re.IGNORECASE)
                if matches:
                    metrics[key] = matches[:3]
                    return

        revenue_patterns = [
            r'(?:total\s+)?(?:net\s+)?(?:revenue|sales)[^\n\$]*\$?\s*([\d,.]+)\s*(million|billion|thousand)?',
            r'revenues?[^\n\$]*\$?\s*([\d,.]+)\s*(million|billion|thousand)?',
        ]
        profit_patterns = [
            r'net\s+income[^\n\$]*\$?\s*([\d,.]+)\s*(million|billion|thousand)?',
            r'net\s+earnings[^\n\$]*\$?\s*([\d,.]+)\s*(million|billion|thousand)?',
        ]
        asset_patterns = [
            r'total\s+assets[^\n\$]*\$?\s*([\d,.]+)\s*(million|billion|thousand)?',
        ]

        extract_values(revenue_patterns, "revenue")
        extract_values(profit_patterns, "net_income")
        extract_values(asset_patterns, "total_assets")

        return metrics
from crewai.tools import BaseTool
class ParseDocTool(BaseTool):
    name: str = "parse_financial_doc"
    description: str = "Parse financial documents (.pdf/.docx/.txt) and return cleaned text"
    args_schema: type[BaseModel] = ParseDocInput
    
    def _run(self, **kwargs) -> str:
        return FinancialDocumentTool.read_document(kwargs["path"])

class ExtractMetricsTool(BaseTool):
    name: str = "extract_financial_metrics"
    description: str = "Extract financial metrics (revenue, net income, assets) from text"
    args_schema: type[BaseModel] = ExtractMetricsInput
    
    def _run(self, **kwargs) -> Dict[str, Any]:
        return FinancialDocumentTool.extract_financial_metrics(kwargs["text"])

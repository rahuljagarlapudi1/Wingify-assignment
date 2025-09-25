import os
import re
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path
import PyPDF2
import pdfplumber
import fitz  # PyMuPDF
from docx import Document as DocxDocument
import httpx
from datetime import datetime
from config.settings import settings

logger = logging.getLogger(__name__)

def search_tool(query: str) -> str:
    """Lightweight web search using Serper.dev via HTTP."""
    api_key = settings.SERPER_API_KEY
    if not api_key:
        logger.warning("SERPER_API_KEY not configured")
        return "Search unavailable: SERPER_API_KEY not set."

    try:
        with httpx.Client(timeout=15) as client:
            resp = client.post(
                "https://google.serper.dev/search",
                headers={"X-API-KEY": api_key, "Content-Type": "application/json"},
                json={"q": query[:200], "num": 5},  # Limit query length
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.TimeoutException:
        logger.warning(f"Search timeout for query: {query}")
        return "Search timeout occurred."
    except Exception as e:
        logger.error(f"Search failed: {e}")
        return f"Search error: {str(e)}"

    items = data.get("organic", [])[:5]
    if not items:
        return "No search results found."

    results = []
    for item in items:
        title = item.get("title", "Untitled")[:100]
        link = item.get("link", "")
        snippet = item.get("snippet", "")[:200]
        results.append(f"• {title}\n  {link}\n  {snippet}")
    return "\n\n".join(results)

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
                
        raise Exception(f"All PDF extractors failed for: {file_path}")

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
                        tables = page.extract_tables()
                        if tables:
                            for table_num, table in enumerate(tables):  # FIXED: was 'for page in tables'
                                table_text = FinancialDocumentTool._format_table_text(table)
                                full_text += f"\n[Table {table_num + 1}]\n{table_text}\n"
                    except Exception as e:
                        logger.debug(f"Table extraction failed on page {page_num}: {e}")
        except Exception as e:
            logger.error(f"pdfplumber extraction failed: {e}")
            raise
        return full_text

    @staticmethod
    def _extract_with_pymupdf(file_path: str) -> str:  # FIXED: Was missing implementation
        """Extract using PyMuPDF."""
        full_text = ""
        try:
            doc = fitz.open(file_path)
            for page_num in range(doc.page_count):
                page = doc[page_num]
                text = page.get_text()
                full_text += f"\n[Page {page_num + 1}]\n{text}\n"
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
        
        # Normalize line endings
        text = re.sub(r'\r\n?', '\n', text)
        
        # Fix multiple spaces but preserve some structure
        text = re.sub(r'[ \t]+', ' ', text)
        text = re.sub(r'\n\s*\n\s*\n', '\n\n', text)
        
        # Fix monetary formatting
        text = re.sub(r'\$\s+', '$', text)
        text = re.sub(r'(\d)\s+,\s*(\d)', r'\1,\2', text)
        
        # Remove common noise
        text = re.sub(r'Page \d+ of \d+', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\n\s*\n', '\n\n', text)
        
        return text.strip()

    @staticmethod
    def extract_financial_metrics(text: str) -> Dict[str, Any]:
        """Extract key financial metrics from text."""
        metrics: Dict[str, Any] = {}
        
        if not text:
            return metrics

        def extract_values(patterns: List[str], key: str) -> None:  # FIXED: Function was defined but never called
            """Extract financial values using regex patterns."""
            for pattern in patterns:
                matches = re.findall(pattern, text, flags=re.IGNORECASE)
                if matches:
                    # Take first 3 matches to avoid noise
                    metrics[key] = matches[:3]
                    return

        # Define extraction patterns
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

        # Extract metrics using fixed function calls
        extract_values(revenue_patterns, "revenue")
        extract_values(profit_patterns, "net_income") 
        extract_values(asset_patterns, "total_assets")

        return metrics

class AnalyticsTracker:
    """Track LLM and tool usage for observability."""
    
    @staticmethod
    def track_llm_call(agent_name: str, task_name: str, tokens_used: int, 
                      response_time: float, success: bool) -> Dict[str, Any]:
        """Track LLM API calls for monitoring."""
        tracking_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "agent_name": agent_name,
            "task_name": task_name,
            "tokens_used": tokens_used,
            "response_time_seconds": round(response_time, 3),
            "success": success,
        }
        
        logger.info(f"LLM Call Tracked: {tracking_data}")
        return tracking_data
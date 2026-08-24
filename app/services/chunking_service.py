from __future__ import annotations

import io
import re
from typing import Any, Dict, List, Optional
from app.core.logging import get_logger

logger = get_logger("services.chunking_service")

# Regex heuristics for detecting academic section headings
_HEADING_PATTERNS = [
    re.compile(r"^(?:#{1,4}\s+|\d+(?:\.\d+)*\s+|[A-Z][A-Z\s0-9_-]{3,60}$)", re.MULTILINE),
    re.compile(r"^(?:SECTION|CHAPTER|PART|MODULE|UNIT|GUIDELINE|POLICY)\s+\d*[:\.\-]?\s*", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^(?:COURSE REGISTRATION|MISSING COURSES|PREREQUISITES|EXAMINATION|ADMISSION|RESULTS|FEES|PORTAL|ACADEMIC CALENDAR)", re.IGNORECASE | re.MULTILINE),
]


def _clean_text(text: str) -> str:
    if not text:
        return ""
    # Normalize unicode spaces and excessive blank lines
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _approx_token_count(text: str) -> int:
    # 1 token is approximately 4 characters or ~0.75 words in English
    return max(1, len(text.split()))


class ChunkingService:
    def __init__(self, target_chunk_tokens: int = 400, overlap_tokens: int = 60):
        self.target_chunk_tokens = target_chunk_tokens
        self.overlap_tokens = overlap_tokens

    def extract_text_from_pdf(self, file_bytes: bytes) -> List[Dict[str, Any]]:
        """Extract text from PDF pages, returning page-tagged text blocks."""
        import pypdf
        reader = pypdf.PdfReader(io.BytesIO(file_bytes))
        pages_content: List[Dict[str, Any]] = []
        for idx, page in enumerate(reader.pages, start=1):
            raw_text = page.extract_text() or ""
            clean = _clean_text(raw_text)
            if clean:
                pages_content.append({"page": idx, "text": clean})
        return pages_content

    def extract_text_from_docx(self, file_bytes: bytes) -> List[Dict[str, Any]]:
        """Extract paragraphs and headings from DOCX."""
        import docx
        doc = docx.Document(io.BytesIO(file_bytes))
        elements: List[Dict[str, Any]] = []
        current_section = "General"
        
        for p in doc.paragraphs:
            text = _clean_text(p.text)
            if not text:
                continue
            # If paragraph is a heading style
            if p.style and ("heading" in p.style.name.lower() or "title" in p.style.name.lower()):
                current_section = text
            elements.append({
                "page": 1,
                "section": current_section,
                "text": text,
            })
        return elements

    def extract_text_from_txt(self, file_bytes: bytes) -> List[Dict[str, Any]]:
        """Extract text from plain text file."""
        text = file_bytes.decode("utf-8", errors="replace")
        clean = _clean_text(text)
        return [{"page": 1, "text": clean}]

    def _split_into_paragraphs(self, text: str) -> List[str]:
        return [p.strip() for p in text.split("\n\n") if p.strip()]

    def _detect_heading(self, line: str) -> Optional[str]:
        cleaned_line = line.strip()
        if len(cleaned_line) < 3 or len(cleaned_line) > 100:
            return None
        # Check markdown heading
        if cleaned_line.startswith("#"):
            return re.sub(r"^#+\s*", "", cleaned_line)
        # Check heading patterns
        for pat in _HEADING_PATTERNS:
            if pat.match(cleaned_line):
                return cleaned_line
        # Check all caps short line
        if cleaned_line.isupper() and len(cleaned_line.split()) <= 8:
            return cleaned_line
        return None

    def chunk_document(
        self,
        file_bytes: bytes,
        filename: str,
        title: str,
        category: str = "general",
        department_id: Optional[str] = None,
        version: int = 1,
    ) -> List[Dict[str, Any]]:
        """
        Processes a raw document file and produces section-aware, overlapping chunks.
        """
        ext = filename.split(".")[-1].lower() if "." in filename else "txt"
        
        raw_sections: List[Dict[str, Any]] = []
        if ext == "pdf":
            page_blocks = self.extract_text_from_pdf(file_bytes)
            for pb in page_blocks:
                p_text = pb["text"]
                paragraphs = self._split_into_paragraphs(p_text)
                cur_sec = "Overview"
                for para in paragraphs:
                    heading = self._detect_heading(para)
                    if heading and len(para) < 120:
                        cur_sec = heading
                    else:
                        raw_sections.append({
                            "page": pb["page"],
                            "section": cur_sec,
                            "text": para,
                        })
        elif ext in ("docx", "doc"):
            raw_sections = self.extract_text_from_docx(file_bytes)
        else:
            txt_blocks = self.extract_text_from_txt(file_bytes)
            for tb in txt_blocks:
                paragraphs = self._split_into_paragraphs(tb["text"])
                cur_sec = "Overview"
                for para in paragraphs:
                    heading = self._detect_heading(para)
                    if heading and len(para) < 120:
                        cur_sec = heading
                    else:
                        raw_sections.append({
                            "page": 1,
                            "section": cur_sec,
                            "text": para,
                        })

        if not raw_sections:
            return []

        # Merge small consecutive paragraphs under the same section into ~300-700 token chunks
        chunks: List[Dict[str, Any]] = []
        chunk_idx = 0

        current_chunk_text = ""
        current_section = raw_sections[0].get("section", "General")
        current_page = raw_sections[0].get("page", 1)

        for sec in raw_sections:
            section_name = sec.get("section") or current_section
            page_num = sec.get("page") or current_page
            para_text = sec.get("text", "")

            # If section changed or adding this paragraph exceeds target chunk size
            tokens_so_far = _approx_token_count(current_chunk_text)
            para_tokens = _approx_token_count(para_text)

            if current_chunk_text and (section_name != current_section or (tokens_so_far + para_tokens > self.target_chunk_tokens)):
                # Flush current chunk
                chunks.append({
                    "title": title,
                    "section": current_section,
                    "content": current_chunk_text.strip(),
                    "page": current_page,
                    "chunk_index": chunk_idx,
                    "category": category,
                    "department_id": department_id,
                    "version": version,
                })
                chunk_idx += 1
                
                # Carry over overlap if same section
                if section_name == current_section:
                    overlap_words = current_chunk_text.split()[-self.overlap_tokens:]
                    current_chunk_text = " ".join(overlap_words) + "\n\n" + para_text
                else:
                    current_chunk_text = para_text
                current_section = section_name
                current_page = page_num
            else:
                if current_chunk_text:
                    current_chunk_text += "\n\n" + para_text
                else:
                    current_chunk_text = para_text
                    current_section = section_name
                    current_page = page_num

        if current_chunk_text.strip():
            chunks.append({
                "title": title,
                "section": current_section,
                "content": current_chunk_text.strip(),
                "page": current_page,
                "chunk_index": chunk_idx,
                "category": category,
                "department_id": department_id,
                "version": version,
            })

        return chunks


_chunking_service: Optional[ChunkingService] = None


def get_chunking_service() -> ChunkingService:
    global _chunking_service
    if _chunking_service is None:
        _chunking_service = ChunkingService()
    return _chunking_service

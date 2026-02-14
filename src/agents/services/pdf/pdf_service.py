"""PDF processing service for extracting content and generating summaries."""

import base64
import hashlib
import io
import logging
from typing import Dict, Tuple

import pdfplumber
import PyPDF2
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate

logger = logging.getLogger(__name__)


class PDFProcessor:
    """Service for processing PDF files and generating AI summaries."""

    def __init__(self):
        """Initialize the PDF processor."""
        self.llm = ChatOpenAI(temperature=0.3, max_tokens=2000)

        # Template for summarizing PDF content
        self.summary_template = PromptTemplate(
            input_variables=["content", "filename"],
            template="""
You are an AI assistant specialized in analyzing project documents and requirements.

Please analyze the following PDF content from "{filename}" and provide a comprehensive summary that will help in generating a business proposal.

PDF Content:
{content}

Please provide a detailed summary that includes:
1. **Project Overview**: What is the main project or business idea?
2. **Key Requirements**: What are the specific technical and business requirements?
3. **Scope & Objectives**: What are the goals and scope of the project?
4. **Technical Specifications**: Any technical details, technologies, or constraints mentioned
5. **Business Context**: Target audience, market, budget considerations, timeline
6. **Success Criteria**: How success will be measured
7. **Key Stakeholders**: Who are the important parties involved
8. **Risks & Challenges**: Any potential issues or challenges mentioned

Focus on extracting actionable information that would be valuable for creating a comprehensive business proposal. Be specific and include relevant details, numbers, and requirements.

Summary:
""",
        )

    def extract_text_from_pdf(
        self, pdf_content: bytes, filename: str
    ) -> Tuple[str, str, int]:
        """Extract text from PDF using multiple methods.

        Args:
            pdf_content: PDF file content as bytes
            filename: Original filename for error reporting

        Returns:
            Tuple of (extracted_text, extraction_method, page_count)
        """
        pdf_file = io.BytesIO(pdf_content)

        # Try pdfplumber first (better for complex layouts)
        try:
            extracted_text = ""
            page_count = 0

            with pdfplumber.open(pdf_file) as pdf:
                page_count = len(pdf.pages)
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        extracted_text += page_text + "\n\n"

            if extracted_text.strip():
                logger.info(
                    f"Successfully extracted text from {filename} using pdfplumber"
                )
                return extracted_text.strip(), "pdfplumber", page_count

        except Exception as e:
            logger.warning(f"pdfplumber failed for {filename}: {e}")

        # Fallback to PyPDF2
        try:
            pdf_file.seek(0)  # Reset file pointer
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            extracted_text = ""
            page_count = len(pdf_reader.pages)

            for page in pdf_reader.pages:
                page_text = page.extract_text()
                if page_text:
                    extracted_text += page_text + "\n\n"

            if extracted_text.strip():
                logger.info(f"Successfully extracted text from {filename} using PyPDF2")
                return extracted_text.strip(), "pypdf2", page_count

        except Exception as e:
            logger.error(f"PyPDF2 also failed for {filename}: {e}")

        # If both methods fail
        raise Exception(
            f"Failed to extract text from {filename} using both pdfplumber and PyPDF2"
        )

    def generate_summary(self, content: str, filename: str) -> str:
        """Generate AI summary of PDF content.

        Args:
            content: Extracted text content
            filename: Original filename

        Returns:
            AI-generated summary
        """
        try:
            # Limit content length to avoid token limits
            max_content_length = 8000  # Leave room for prompt and response
            if len(content) > max_content_length:
                content = (
                    content[:max_content_length]
                    + "\n\n[Content truncated due to length...]"
                )

            # Generate summary using LangChain
            chain = self.summary_template | self.llm
            summary = chain.invoke({"content": content, "filename": filename})

            # Clean up the response
            if hasattr(summary, "content"):
                summary = summary.content
            elif hasattr(summary, "text"):
                summary = summary.text

            return str(summary).strip()

        except Exception as e:
            logger.error(f"Failed to generate summary for {filename}: {e}")
            # Return a basic summary if AI fails
            return f"""
**Project Document Summary for {filename}**

This document contains project requirements and specifications. Key content includes:

- Document length: {len(content)} characters
- Content preview: {content[:500]}...

Note: AI summarization failed, showing raw content preview instead.
Please review the full document content for complete details.
"""

    def calculate_file_hash(self, content: bytes) -> str:
        """Calculate SHA-256 hash of file content."""
        return hashlib.sha256(content).hexdigest()

    def process_pdf_file(self, pdf_content: bytes, filename: str) -> Dict:
        """Process a PDF file completely - extract text and generate summary.

        Args:
            pdf_content: PDF file content as bytes
            filename: Original filename

        Returns:
            Dict with processing results
        """
        try:
            # Calculate file hash
            file_hash = self.calculate_file_hash(pdf_content)
            file_size = len(pdf_content)

            # Extract text
            raw_content, extraction_method, page_count = self.extract_text_from_pdf(
                pdf_content, filename
            )

            # Generate summary
            content_summary = self.generate_summary(raw_content, filename)

            return {
                "success": True,
                "file_hash": file_hash,
                "file_size": file_size,
                "raw_content": raw_content,
                "content_summary": content_summary,
                "extraction_method": extraction_method,
                "page_count": page_count,
                "error": None,
            }

        except Exception as e:
            logger.error(f"Failed to process PDF {filename}: {e}")
            return {
                "success": False,
                "file_hash": (
                    self.calculate_file_hash(pdf_content) if pdf_content else None
                ),
                "file_size": len(pdf_content) if pdf_content else 0,
                "raw_content": "",
                "content_summary": "",
                "extraction_method": "manual",
                "page_count": 0,
                "error": str(e),
            }

    def process_base64_pdf(self, base64_content: str, filename: str) -> Dict:
        """Process a base64-encoded PDF file.

        Args:
            base64_content: Base64 encoded PDF content
            filename: Original filename

        Returns:
            Dict with processing results
        """
        try:
            # Decode base64 content
            pdf_content = base64.b64decode(base64_content)
            return self.process_pdf_file(pdf_content, filename)

        except Exception as e:
            logger.error(f"Failed to decode base64 PDF {filename}: {e}")
            return {
                "success": False,
                "file_hash": None,
                "file_size": 0,
                "raw_content": "",
                "content_summary": "",
                "extraction_method": "manual",
                "page_count": 0,
                "error": f"Base64 decoding failed: {str(e)}",
            }


# Global instance
pdf_processor = PDFProcessor()

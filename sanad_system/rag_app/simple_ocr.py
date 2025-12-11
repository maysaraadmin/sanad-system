"""
Simple OCR service for RAG document processing
Direct implementation using PaddleOCR without complex dependencies
"""

import logging
import os
from typing import Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class SimpleOCRService:
    """Simple OCR service for extracting text from scanned PDFs"""
    
    def __init__(self):
        self.paddle_ocr = None
        self._init_paddle_ocr()
    
    def _init_paddle_ocr(self):
        """Initialize PaddleOCR directly"""
        try:
            # Direct import without complex dependencies
            from paddleocr import PaddleOCR
            self.paddle_ocr = PaddleOCR(use_angle_cls=True, lang='ar')
            logger.info("Simple PaddleOCR initialized for Arabic")
        except ImportError:
            logger.warning("PaddleOCR not available")
            self.paddle_ocr = None
        except Exception as e:
            logger.error(f"Failed to initialize PaddleOCR: {e}")
            self.paddle_ocr = None
    
    def extract_text_from_pdf(self, file_path: str, max_pages: int = 3) -> str:
        """Extract text from PDF using OCR"""
        if not self.paddle_ocr:
            return ""
        
        try:
            from pdf2image import convert_from_path
            
            # Convert first few pages to images
            images = convert_from_path(file_path, first_page=1, last_page=max_pages)
            
            full_text = ""
            for i, image in enumerate(images):
                try:
                    result = self.paddle_ocr.ocr(image, cls=True)
                    
                    page_text = ""
                    if result and result[0]:
                        for line in result[0]:
                            if line and len(line) > 1:
                                page_text += line[1][0] + "\n"
                    
                    if page_text.strip():
                        full_text += f"--- الصفحة {i+1} ---\n{page_text}\n"
                    
                    logger.info(f"OCR processed page {i+1}, extracted {len(page_text)} characters")
                    
                except Exception as e:
                    logger.warning(f"Error processing page {i+1}: {e}")
                    continue
            
            return full_text.strip()
            
        except ImportError:
            logger.warning("pdf2image not available")
            return ""
        except Exception as e:
            logger.error(f"Error in PDF OCR extraction: {e}")
            return ""

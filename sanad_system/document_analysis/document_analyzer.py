import os
import re
import logging
import json
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from PIL import Image
import numpy as np

# Configure logging
logger = logging.getLogger(__name__)

class DocumentAnalyzer:
    def __init__(self, device: str = None):
        print("=== DocumentAnalyzer Initializing ===")
        try:
            import torch
            self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        except ImportError:
            self.device = "cpu"
            logger.warning("PyTorch not available, using CPU")
        self._initialize_models()
        print("=== DocumentAnalyzer Initialized ===")
    
    def _initialize_models(self):
        """Initialize all required models for Arabic document analysis"""
        logger.info("Initializing Arabic Document Analysis models...")
        
        # Try to initialize PaddleOCR (best for Arabic)
        try:
            from paddleocr import PaddleOCR
            logger.info("Importing PaddleOCR...")
            self.paddle_ocr = PaddleOCR(use_angle_cls=True, lang='ar', show_log=False)
            logger.info("PaddleOCR initialized successfully for Arabic")
        except Exception as e:
            self.paddle_ocr = None
            logger.error(f"PaddleOCR initialization failed: {str(e)}")
        
        # Try to initialize Tesseract OCR
        try:
            import pytesseract
            self.ocr = True
            logger.info("Tesseract OCR available")
        except ImportError:
            self.ocr = None
            logger.warning("Tesseract not available")
        
        # For now, skip LayoutLM and Donut due to compatibility issues
        logger.info("Skipping LayoutLM and Donut due to compatibility issues")
        self.layout_processor = None
        self.layout_model = None
        self.donut_processor = None
        self.donut_model = None
    
    def analyze_document(self, file_path: str) -> Dict:
        """Main method to analyze a document"""
        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File not found: {file_path}")

            logger.info(f"Analyzing document: {file_path}")
            
            # Extract text
            logger.info("Extracting text...")
            extracted_text = self.extract_text(file_path)
            logger.info(f"Extracted text length: {len(extracted_text)} characters")
            
            if not extracted_text.strip():
                logger.warning("No text was extracted from the document")
                extracted_text = "No text could be extracted from this document. The file might be an image-only PDF, corrupted, or in an unsupported format."

            result = {
                'status': 'success',
                'extracted_text': extracted_text,
                'analysis': self._analyze_text(extracted_text),
                'models_used': {
                    'paddleocr': self.paddle_ocr is not None,
                    'tesseract': self.ocr is not None,
                    'layoutlm': False,
                    'donut': False,
                    'basic_extraction': True
                }
            }
            
            # Ensure the result is JSON serializable
            return json.loads(json.dumps(result, ensure_ascii=False))

        except Exception as e:
            logger.error(f"Document analysis failed: {str(e)}")
            return {
                "status": "error",
                "message": str(e),
                "extracted_text": f"Error during analysis: {str(e)}",
                "analysis": {"error": str(e)}
            }
    
    def _analyze_layout(self, file_path: str) -> Dict:
        """Analyze document layout using LayoutLM"""
        if not self.layout_processor or not self.layout_model:
            return {"message": "LayoutLM not available"}
        
        try:
            # Convert PDF to image if needed
            if file_path.lower().endswith('.pdf'):
                images = convert_from_path(file_path, dpi=200)
                if images:
                    image = images[0]
                else:
                    return {"message": "Could not convert PDF to image"}
            else:
                image = Image.open(file_path)
            
            # Process with LayoutLM
            encoding = self.layout_processor(image, return_tensors="pt")
            if self.device != "cpu":
                encoding = {k: v.to(self.device) for k, v in encoding.items()}
            
            with torch.no_grad():
                outputs = self.layout_model(**encoding)
            
            # Get predictions
            predictions = outputs.logits.argmax(-1)
            
            return {
                "status": "success",
                "predictions": predictions.tolist()[:10],  # First 10 predictions
                "message": "Layout analysis completed"
            }
            
        except Exception as e:
            logger.error(f"Layout analysis failed: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    def _analyze_with_donut(self, file_path: str) -> Dict:
        """Analyze document using Donut model"""
        if not self.donut_processor or not self.donut_model:
            return {"message": "Donut not available"}
        
        try:
            # Convert PDF to image if needed
            if file_path.lower().endswith('.pdf'):
                images = convert_from_path(file_path, dpi=200)
                if images:
                    image = images[0]
                else:
                    return {"message": "Could not convert PDF to image"}
            else:
                image = Image.open(file_path)
            
            # Process with Donut
            prompt = "<s_docvqa><s_question></s_question>"
            pixel_values = self.donut_processor(image, return_tensors="pt").pixel_values
            if self.device != "cpu":
                pixel_values = pixel_values.to(self.device)
            
            with torch.no_grad():
                outputs = self.donut_model.generate(
                    pixel_values,
                    max_length=self.donut_processor.tokenizer.model_max_length,
                    num_beams=4,
                    early_stopping=True
                )
            
            # Decode the output
            decoded_text = self.donut_processor.batch_decode(outputs, skip_special_tokens=True)[0]
            
            return {
                "status": "success",
                "extracted_info": decoded_text,
                "message": "Donut analysis completed"
            }
            
        except Exception as e:
            logger.error(f"Donut analysis failed: {str(e)}")
            return {"status": "error", "message": str(e)}

    def extract_text(self, file_path: str) -> str:
        """Extract text using available OCR methods"""
        try:
            logger.info(f"Starting text extraction for: {file_path}")
            logger.info(f"PaddleOCR available: {self.paddle_ocr is not None}")
            logger.info(f"Tesseract available: {self.ocr is not None}")
            
            # Try PaddleOCR first (best for Arabic)
            if self.paddle_ocr:
                logger.info("Using PaddleOCR for text extraction")
                return self._extract_with_paddleocr(file_path)
            # Fall back to Tesseract OCR
            elif self.ocr:
                logger.info("Using Tesseract for text extraction")
                return self._extract_with_tesseract(file_path)
            else:
                logger.info("Using basic text extraction")
                # Fallback to basic text extraction
                return self._basic_text_extraction(file_path)
        except Exception as e:
            logger.error(f"Error in text extraction: {str(e)}")
            return self._basic_text_extraction(file_path)
    
    def _extract_with_paddleocr(self, file_path: str) -> str:
        """Extract text using PaddleOCR (best for Arabic)"""
        try:
            logger.info(f"Starting PaddleOCR extraction for: {file_path}")
            
            if file_path.lower().endswith('.pdf'):
                from pdf2image import convert_from_path
                logger.info("Converting PDF to images...")
                images = convert_from_path(file_path, dpi=200)
                if not images:
                    raise ValueError("Could not extract images from PDF")
                
                # Process first few pages for performance
                max_pages = min(len(images), 3)  # Reduce to 3 pages for faster testing
                logger.info(f"Processing {max_pages} pages with PaddleOCR")
                
                text = ""
                for i, image in enumerate(images[:max_pages]):
                    logger.info(f"Processing page {i+1} with PaddleOCR")
                    try:
                        result = self.paddle_ocr.ocr(np.array(image), cls=True)
                        page_text = ""
                        if result:
                            for line in result:
                                if line:
                                    for word_info in line:
                                        if word_info and len(word_info) > 1:
                                            page_text += word_info[1][0] + " "
                        
                        if page_text.strip():
                            text += f"Page {i+1} (PaddleOCR):\n{page_text}\n\n"
                            logger.info(f"Extracted {len(page_text)} characters from page {i+1}")
                        else:
                            logger.warning(f"No text extracted from page {i+1}")
                            text += f"Page {i+1} (PaddleOCR): No text detected\n\n"
                    except Exception as e:
                        logger.error(f"Error processing page {i+1}: {str(e)}")
                        text += f"Page {i+1} (PaddleOCR): Error - {str(e)}\n\n"
                
                if not text.strip():
                    text = "PaddleOCR could not extract text from this PDF. The pages might be too complex or the text quality too low."
                
                return text.strip()
            else:
                # Process image file directly
                logger.info("Processing image file with PaddleOCR")
                from PIL import Image
                image = Image.open(file_path)
                result = self.paddle_ocr.ocr(np.array(image), cls=True)
                text = ""
                for line in result:
                    if line:
                        for word_info in line:
                            if word_info and len(word_info) > 1:
                                text += word_info[1][0] + " "
                return text.strip() if text.strip() else "No text detected in image"
                
        except Exception as e:
            logger.error(f"PaddleOCR extraction failed: {str(e)}")
            return f"PaddleOCR Error: {str(e)}"
    
    def _extract_with_tesseract(self, file_path: str) -> str:
        """Extract text using Tesseract OCR"""
        try:
            import pytesseract
            from PIL import Image
            
            # Convert PDF to images if needed
            if file_path.lower().endswith('.pdf'):
                try:
                    from pdf2image import convert_from_path
                    images = convert_from_path(file_path, dpi=200)
                    if not images:
                        raise ValueError("Could not extract images from PDF")
                    
                    # Process all pages
                    text = ""
                    for i, image in enumerate(images):
                        page_text = pytesseract.image_to_string(image, lang='ara+eng')
                        text += f"Page {i+1}:\n{page_text}\n\n"
                    return text.strip()
                except ImportError:
                    logger.warning("pdf2image not available, falling back to basic PDF extraction")
                    return self._basic_text_extraction(file_path)
            else:
                # Process image file directly
                image = Image.open(file_path)
                text = pytesseract.image_to_string(image, lang='ara+eng')
            
            return text.strip()
            
        except Exception as e:
            logger.error(f"Tesseract extraction failed: {str(e)}")
            return self._basic_text_extraction(file_path)

    def _basic_text_extraction(self, file_path: str) -> str:
        """Basic text extraction fallback"""
        try:
            file_ext = Path(file_path).suffix.lower()
            logger.info(f"Extracting text from {file_ext} file: {file_path}")
            
            if file_ext == '.pdf':
                import PyPDF2
                try:
                    with open(file_path, 'rb') as file:
                        reader = PyPDF2.PdfReader(file)
                        num_pages = len(reader.pages)
                        logger.info(f"PDF has {num_pages} pages")
                        
                        # For very large PDFs, only process first few pages
                        max_pages = min(num_pages, 10)  # Limit to first 10 pages for performance
                        
                        text = ""
                        for page_num in range(max_pages):
                            try:
                                page = reader.pages[page_num]
                                page_text = page.extract_text()
                                if page_text and page_text.strip():
                                    text += f"Page {page_num + 1}:\n{page_text}\n\n"
                                else:
                                    logger.debug(f"No text extracted from page {page_num + 1}")
                            except Exception as e:
                                logger.error(f"Error extracting page {page_num + 1}: {str(e)}")
                        
                        if not text.strip():
                            if num_pages > max_pages:
                                text = f"This is a large image-based PDF with {num_pages} pages. Only the first {max_pages} pages were checked for text. The PDF appears to be image-based and requires OCR for full text extraction."
                            else:
                                text = f"This PDF appears to be image-based or contains no extractable text. It has {num_pages} pages and requires OCR for text extraction."
                        
                        return text.strip()
                except Exception as e:
                    logger.error(f"PDF reading error: {str(e)}")
                    return f"Error reading PDF: {str(e)}"
                    
            elif file_ext in ('.docx', '.doc'):
                import docx
                try:
                    doc = docx.Document(file_path)
                    text = ""
                    for paragraph in doc.paragraphs:
                        if paragraph.text.strip():
                            text += paragraph.text + "\n"
                    return text.strip() if text.strip() else "No text found in document"
                except Exception as e:
                    logger.error(f"DOCX reading error: {str(e)}")
                    return f"Error reading DOCX: {str(e)}"
                
            elif file_ext in ('.txt', '.text'):
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
                        content = file.read()
                        return content.strip() if content.strip() else "Empty text file"
                except Exception as e:
                    logger.error(f"Text file reading error: {str(e)}")
                    return f"Error reading text file: {str(e)}"
                    
            elif file_ext in ('.jpg', '.jpeg', '.png', '.bmp', '.tiff'):
                # For image files, try OCR if available
                if self.ocr:
                    return self._extract_with_tesseract(file_path)
                else:
                    return "Image file detected but OCR (pytesseract) is not available. Please install pytesseract for image text extraction."
            
            else:
                logger.warning(f"Unsupported file type: {file_ext}")
                return f"Unsupported file type: {file_ext}. Supported formats: PDF, DOCX, TXT, and image files"
                
        except Exception as e:
            logger.error(f"Basic extraction failed for {file_path}: {str(e)}")
            return f"Error extracting text: {str(e)}"

    def _analyze_text(self, text: str) -> Dict:
        """Analyze extracted text"""
        if not text:
            return {"message": "No text extracted"}
        
        # Basic text analysis
        words = text.split()
        sentences = text.split('.')
        
        return {
            "word_count": len(words),
            "sentence_count": len(sentences),
            "character_count": len(text),
            "preview": text[:500] + "..." if len(text) > 500 else text
        }

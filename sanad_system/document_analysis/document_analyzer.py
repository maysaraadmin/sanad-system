import os
import logging
import time
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from django.conf import settings
from PIL import Image
import pytesseract
import PyPDF2
import arabic_reshaper
from bidi.algorithm import get_display
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import re
from difflib import SequenceMatcher
from collections import Counter

logger = logging.getLogger(__name__)

class DocumentAnalyzer:
    _instance = None
    _initialized = False
    
    def __new__(cls, device: str = None):
        if cls._instance is None:
            cls._instance = super(DocumentAnalyzer, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, device: str = None):
        if self._initialized:
            return
        
        logger.info("=== DocumentAnalyzer Initializing ===")
        try:
            import torch
            self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        except ImportError:
            self.device = "cpu"
            logger.warning("PyTorch not available, using CPU")
        
        self._initialize_models()
        self._initialized = True
        logger.info("=== DocumentAnalyzer Initialized ===")
    
    def _initialize_models(self):
        """Initialize all required models for Arabic document analysis"""
        logger.info("Initializing Arabic Document Analysis models...")
        
        # Try to initialize PaddleOCR (best for Arabic)
        try:
            from paddleocr import PaddleOCR
            logger.info("Importing PaddleOCR...")
            # Disable PaddleOCR initialization messages and prevent reinitialization
            import os
            os.environ['FLAGS_allocator_strategy'] = 'auto_growth'
            os.environ['FLAGS_memory_fraction_of_eager_deletion'] = '1.0'
            os.environ['FLAGS_max_inference_batch_size'] = '1'
            os.environ['FLAGS_use_mkldnn'] = 'false'
            os.environ['FLAGS_enable_pir_api'] = 'false'
            os.environ['FLAGS_cudnn_deterministic'] = 'true'
            os.environ['FLAGS_check_nan_inf'] = 'false'
            os.environ['FLAGS_eager_delete_tensor_gb'] = '0.0'
            os.environ['FLAGS_fast_eager_deletion_mode'] = 'true'
            
            # Try different initialization approaches
            try:
                self.paddle_ocr = PaddleOCR(
                    use_angle_cls=True, 
                    lang='ar',
                    show_log=False,
                    use_gpu=False,  # Force CPU to avoid GPU issues
                    det_db_thresh=0.3,  # Lower threshold for better detection
                    det_db_box_thresh=0.5,
                    rec_batch_num=1  # Process one by one to avoid memory issues
                )
                logger.info("PaddleOCR initialized successfully for Arabic (with angle classification)")
            except Exception as e1:
                logger.warning(f"First PaddleOCR init failed: {str(e1)}")
                try:
                    self.paddle_ocr = PaddleOCR(
                        lang='ar',
                        show_log=False,
                        use_gpu=False,
                        det_db_thresh=0.3,
                        det_db_box_thresh=0.5,
                        rec_batch_num=1
                    )
                    logger.info("PaddleOCR initialized successfully for Arabic (basic)")
                except Exception as e2:
                    logger.error(f"Second PaddleOCR init failed: {str(e2)}")
                    self.paddle_ocr = None
        except ImportError:
            self.paddle_ocr = None
            logger.warning("PaddleOCR not available")
        
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
    
    def analyze_document(self, file_path: str) -> dict:
        """Analyze document with enhanced Arabic support"""
        try:
            logger.info(f"Starting enhanced document analysis for: {file_path}")
            
            # Extract text with improved OCR
            extracted_text = self.extract_text(file_path)
            
            # Create a working analysis structure
            if not extracted_text.strip() or extracted_text == "لا يوجد نص مستخرج" or "Error" in extracted_text or "No text detected" in extracted_text:
                return {
                    "word_count": 0,
                    "sentence_count": 0,
                    "character_count": 0,
                    "preview": "لا يوجد نص مستخرج",
                    "status": "completed",
                    "message": "لا يمكن استخراج نص من المستند",
                    "is_arabic": False,
                    "models_used": ["basic_extraction"],
                    "sentiment": "neutral",
                    "top_keywords": [],
                    "reading_time_minutes": 0,
                    "corrections_made": False
                }
            
            # Enhanced Arabic analysis
            try:
                analysis = self._enhance_arabic_analysis(extracted_text)
                # Add hadith comparison if text contains hadith-like content
                if analysis.get("is_arabic", False):
                    analysis["hadith_comparison"] = self._compare_with_hadiths(extracted_text)
            except Exception as analysis_error:
                logger.error(f"Arabic analysis failed: {str(analysis_error)}")
                # Fallback to basic analysis
                words = extracted_text.split()
                analysis = {
                    "word_count": len(words),
                    "sentence_count": len(extracted_text.split('.')),
                    "character_count": len(extracted_text),
                    "preview": extracted_text[:500] + ("..." if len(extracted_text) > 500 else ""),
                    "language": "unknown",
                    "is_arabic": False,
                    "sentiment": "neutral",
                    "top_keywords": words[:5] if words else [],
                    "reading_time_minutes": round(len(words) / 180, 1) if words else 0,
                    "corrections_made": False
                }
            
            analysis.update({
                "status": "completed",
                "models_used": ["paddleocr_enhanced"],
                "extraction_method": "paddleocr_enhanced"
            })
            
            return analysis
            
        except Exception as e:
            logger.error(f"Document analysis failed: {str(e)}")
            return {
                "word_count": 0,
                "sentence_count": 0,
                "character_count": 0,
                "preview": f"خطأ في التحليل: {str(e)}",
                "status": "error",
                "message": f"فشل تحليل المستند: {str(e)}",
                "is_arabic": False,
                "sentiment": "neutral",
                "top_keywords": [],
                "reading_time_minutes": 0,
                "corrections_made": False
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
                result = self._extract_with_paddleocr(file_path)
                # Check if PaddleOCR actually extracted meaningful text
                if result and len(result.strip()) > 10 and not any(keyword in result for keyword in ["Error", "No text detected", "could not extract", "Error:"]):
                    logger.info(f"PaddleOCR successfully extracted {len(result)} characters")
                    return result
                else:
                    logger.warning("PaddleOCR failed to extract meaningful text, trying Tesseract")
            
            # Fall back to Tesseract OCR
            if self.ocr:
                logger.info("Using Tesseract for text extraction")
                result = self._extract_with_tesseract(file_path)
                if result and len(result.strip()) > 10 and not any(keyword in result for keyword in ["Error", "No text detected", "could not extract", "Error:"]):
                    logger.info(f"Tesseract successfully extracted {len(result)} characters")
                    return result
                else:
                    logger.warning("Tesseract failed, trying basic extraction")
            
            # Fallback to basic text extraction
            logger.info("Using basic text extraction")
            return self._basic_text_extraction(file_path)
            
        except Exception as e:
            logger.error(f"Error in text extraction: {str(e)}")
            return self._basic_text_extraction(file_path)
    
    def _extract_with_paddleocr(self, file_path: str) -> str:
        """Extract text using PaddleOCR with enhanced settings for Arabic"""
        try:
            logger.info(f"Starting enhanced PaddleOCR extraction for: {file_path}")
            
            if file_path.lower().endswith('.pdf'):
                # Try with pdf2image first
                try:
                    from pdf2image import convert_from_path
                    logger.info("Converting PDF to high-res images (300 DPI)...")
                    images = convert_from_path(
                        file_path, 
                        dpi=300,  # Increased from 200 to 300 DPI
                        thread_count=4,  # Use multiple threads for faster processing
                        grayscale=True,  # Better for text
                        fmt='jpeg',
                        jpegopt={'quality': 95, 'optimize': True, 'progressive': True}
                    )
                except Exception as pdf_error:
                    logger.warning(f"PDF to image conversion failed: {str(pdf_error)}")
                    # Fallback to basic PDF processing
                    return self._fallback_pdf_extraction(file_path)
                
                if not images:
                    logger.warning("No images extracted from PDF, trying fallback method")
                    return self._fallback_pdf_extraction(file_path)
                
                # Process up to the configurable page limit (default: all pages)
                from django.conf import settings
                page_limit = getattr(settings, 'OCR_MAX_PAGES', len(images))
                max_pages = min(len(images), page_limit)
                logger.info(f"Processing {max_pages} pages with enhanced PaddleOCR")
                
                text = ""
                for i, image in enumerate(images[:max_pages]):
                    logger.info(f"Processing page {i+1} with enhanced PaddleOCR")
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
                            text += f"Page {i+1} (Enhanced PaddleOCR):\n{page_text}\n\n"
                            logger.info(f"Extracted {len(page_text)} characters from page {i+1}")
                        else:
                            logger.warning(f"No text extracted from page {i+1}")
                            text += f"Page {i+1} (Enhanced PaddleOCR): No text detected\n\n"
                    except Exception as e:
                        logger.error(f"Error processing page {i+1}: {str(e)}")
                        text += f"Page {i+1} (Enhanced PaddleOCR): Error - {str(e)}\n\n"
                
                if not text.strip():
                    text = "Enhanced PaddleOCR could not extract text from this PDF. The pages might be too complex or the text quality too low."
                
                return text.strip()
            else:
                # Process image file directly
                logger.info("Processing image file with enhanced PaddleOCR")
                from PIL import Image
                with Image.open(file_path) as image:
                    img_array = np.array(image)
                result = self.paddle_ocr.ocr(img_array, cls=True)
                text = ""
                for line in result:
                    if line:
                        for word_info in line:
                            if word_info and len(word_info) > 1:
                                text += word_info[1][0] + " "
                return text.strip() if text.strip() else "No text detected in image"
                
        except Exception as e:
            logger.error(f"Enhanced PaddleOCR extraction failed: {str(e)}")
            return f"Enhanced PaddleOCR Error: {str(e)}"
    
    def _fallback_pdf_extraction(self, file_path: str) -> str:
        """Fallback PDF extraction when pdf2image fails"""
        try:
            import PyPDF2
            logger.info("Using fallback PDF extraction with PyPDF2")
            
            with open(file_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                num_pages = len(reader.pages)
                logger.info(f"PDF has {num_pages} pages")
                
                # Configurable page limit (default: all pages)
                from django.conf import settings
                page_limit = getattr(settings, 'OCR_MAX_PAGES', num_pages)
                max_pages = min(num_pages, page_limit)

                text = ""
                for page_num in range(max_pages):
                    try:
                        page = reader.pages[page_num]
                        page_text = page.extract_text()
                        if page_text and page_text.strip():
                            text += f"Page {page_num + 1} (Basic Extraction):\n{page_text}\n\n"
                        else:
                            logger.debug(f"No text extracted from page {page_num + 1}")
                    except Exception as e:
                        logger.error(f"Error extracting page {page_num + 1}: {str(e)}")
                
                if not text.strip():
                    text = f"This PDF appears to be image-based with {num_pages} pages. Poppler is required for OCR processing. Please install Poppler for full text extraction."
                
                return text.strip()
                
        except Exception as e:
            logger.error(f"Fallback PDF extraction failed: {str(e)}")
            return f"PDF Error: {str(e)}"
    
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
                with Image.open(file_path) as image:
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
                                text = f"هذا ملف PDF كبير يحتوي على {num_pages} صفحة. تم فحص أول {max_pages} صفحات فقط. يبدو أن الملف يعتمد على الصور ويتطلب OCR لاستخراج النص الكامل."
                            else:
                                text = f"هذا ملف PDF يعتمد على الصور أو لا يحتوي على نص قابل للاستخراج. يحتوي على {num_pages} صفحة ويتطلب معالجة OCR لاستخراج النص."
                        
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

    def _enhance_arabic_analysis(self, text: str) -> dict:
        """Enhance Arabic text analysis with additional metrics"""
        try:
            import re
            from collections import Counter
            
            # Fix common OCR errors
            corrections = {
                'السالم': 'السلام',
                'حفظك': 'حفظك',
                'رحمه': 'رحمه',
                'اللة': 'الله',
                'محمد': 'محمد',
                'اسلام': 'إسلام',
                'قران': 'قرآن',
                'اللهم': 'اللهم',
                'الحمد': 'الحمد',
                'شكر': 'شكر',
                # Add more corrections as needed
            }
            
            original_text = text
            for wrong, correct in corrections.items():
                text = text.replace(wrong, correct)
            
            # Basic stats
            words = re.findall(r'[\u0600-\u06FF]+', text)
            sentences = re.split(r'[.!?]+', text)
            
            # Remove empty strings
            words = [w for w in words if w.strip()]
            sentences = [s.strip() for s in sentences if s.strip()]
            
            # Word frequency (top 10)
            word_freq = Counter(words).most_common(10)
            
            # Estimate reading time (average Arabic reading speed: 180 WPM)
            reading_time = len(words) / 180  # in minutes
            
            # Simple sentiment analysis for Arabic
            positive_words = ['خير', 'جميل', 'ممتاز', 'حسن', 'ناجح', 'مبارك', 'شكر', 'حمد']
            negative_words = ['سيء', 'فشل', 'خطأ', 'صعب', 'مشكلة', 'خطر', 'خسارة']
            
            positive_count = sum(1 for word in words if word in positive_words)
            negative_count = sum(1 for word in words if word in negative_words)
            
            sentiment = 'neutral'
            if positive_count > negative_count:
                sentiment = 'positive'
            elif negative_count > positive_count:
                sentiment = 'negative'
            
            return {
                "word_count": len(words),
                "sentence_count": len(sentences),
                "character_count": len(text),
                "reading_time_minutes": round(reading_time, 1),
                "top_keywords": [word for word, _ in word_freq],
                "sentiment": sentiment,
                "corrections_made": text != original_text,
                "preview": text[:500] + ("..." if len(text) > 500 else ""),
                "language": "ar",
                "is_arabic": True
            }
        except Exception as e:
            logger.error(f"Arabic analysis enhancement failed: {str(e)}")
            return {
                "word_count": len(text.split()),
                "sentence_count": len(text.split('.')),
                "character_count": len(text),
                "preview": text[:500],
                "language": "unknown",
                "is_arabic": False
            }
    
    def _compare_with_hadiths(self, text: str) -> dict:
        """Compare extracted text with hadiths in the database"""
        try:
            from hadith_app.models import Hadith
            
            # Get all hadiths
            hadiths = Hadith.objects.all()
            
            if not hadiths.exists():
                return {
                    "status": "no_hadiths",
                    "message": "لا توجد أحاديث في قاعدة البيانات للمقارنة",
                    "matches": []
                }
            
            # Prepare text for comparison
            text_clean = self._clean_arabic_text(text)
            text_words = set(text_clean.split())
            
            matches = []
            best_match = None
            best_similarity = 0
            
            for hadith in hadiths:  # Check all hadiths for comprehensive comparison
                hadith_clean = self._clean_arabic_text(hadith.text)
                hadith_words = set(hadith_clean.split())
                
                # Calculate similarity using multiple methods
                similarity_scores = []
                
                # 1. Jaccard similarity (word overlap)
                jaccard_sim = len(text_words & hadith_words) / len(text_words | hadith_words) if text_words | hadith_words else 0
                similarity_scores.append(jaccard_sim)
                
                # 2. Sequence matcher similarity
                seq_sim = SequenceMatcher(None, text_clean, hadith_clean).ratio()
                similarity_scores.append(seq_sim)
                
                # 3. TF-IDF cosine similarity (if sklearn is available)
                try:
                    vectorizer = TfidfVectorizer()
                    tfidf_matrix = vectorizer.fit_transform([text_clean, hadith_clean])
                    cosine_sim = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
                    similarity_scores.append(cosine_sim)
                except:
                    pass
                
                # Calculate average similarity
                avg_similarity = sum(similarity_scores) / len(similarity_scores)
                
                # Consider it a match if similarity > 0.3
                if avg_similarity > 0.3:
                    match_info = {
                        "hadith_id": hadith.id,
                        "hadith_text": hadith.text[:200] + "..." if len(hadith.text) > 200 else hadith.text,
                        "source": hadith.source,
                        "grade": hadith.get_grade_display() if hadith.grade else "غير مصنف",
                        "similarity": round(avg_similarity, 3),
                        "jaccard_similarity": round(jaccard_sim, 3),
                        "sequence_similarity": round(seq_sim, 3)
                    }
                    matches.append(match_info)
                
                # Track best match (always create the match_info)
                current_match = {
                    "hadith_id": hadith.id,
                    "hadith_text": hadith.text[:200] + "..." if len(hadith.text) > 200 else hadith.text,
                    "source": hadith.source,
                    "grade": hadith.get_grade_display() if hadith.grade else "غير مصنف",
                    "similarity": round(avg_similarity, 3),
                    "jaccard_similarity": round(jaccard_sim, 3),
                    "sequence_similarity": round(seq_sim, 3)
                }
                
                if avg_similarity > best_similarity:
                    best_similarity = avg_similarity
                    best_match = current_match
            
            # Sort matches by similarity
            matches.sort(key=lambda x: x["similarity"], reverse=True)
            
            result = {
                "status": "completed",
                "total_hadiths_checked": hadiths.count(),
                "matches_found": len(matches),
                "best_similarity": round(best_similarity, 3),
                "matches": matches[:5]  # Return top 5 matches
            }
            
            if best_match and best_similarity > 0.7:
                result["message"] = f"تم العثور على تطابق قوي مع حديث من {best_match['source']}"
            elif matches:
                result["message"] = f"تم العثور على {len(matches)} تطابقات محتملة"
            else:
                result["message"] = "لم يتم العثور على تطابقات واضحة مع الأحاديث المعروفة"
            
            return result
            
        except Exception as e:
            logger.error(f"Hadith comparison failed: {str(e)}")
            return {
                "status": "error",
                "message": f"فشلت المقارنة مع الأحاديث: {str(e)}",
                "matches": []
            }
    
    def _clean_arabic_text(self, text: str) -> str:
        """Clean and normalize Arabic text for comparison"""
        # Remove control characters (like \u0002, \u0004, etc.)
        text = re.sub(r'[\u0000-\u001F\u007F-\u009F]', '', text)
        
        # Remove diacritics (tashkeel)
        text = re.sub(r'[\u064B-\u065F\u0670\u0674\u06D6-\u06DC\u06DF-\u06E8\u06EA-\u06ED]', '', text)
        
        # Normalize Arabic characters
        text = re.sub(r'[أإآ]', 'ا', text)  # Normalize alef variations
        text = re.sub(r'[يى]', 'ي', text)   # Normalize yeh variations
        text = re.sub(r'ة', 'ه', text)      # Normalize teh marbuta
        
        # Remove punctuation and special characters
        text = re.sub(r'[^\u0600-\u06FF\s]', ' ', text)
        
        # Remove extra spaces and normalize whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text

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

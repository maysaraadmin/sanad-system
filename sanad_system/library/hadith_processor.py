import re
from io import BytesIO
from PyPDF2 import PdfReader
from docx import Document as DocxDocument
from django.utils.translation import gettext_lazy as _
import pytesseract


def extract_text_from_pdf(uploaded_file, start_page=0, end_page=None, chunk_size=5, use_ocr=False, progress_callback=None):
    """Extract text from a PDF file with support for Arabic text, OCR, and chunked processing.
    
    Args:
        uploaded_file: The uploaded PDF file
        start_page: Page number to start from (0-based)
        end_page: Page number to end at (inclusive), None for all pages
        chunk_size: Number of pages to process in memory at once
        use_ocr: Whether to use OCR for text extraction (for image-based PDFs)
        progress_callback: Callback function to report progress (progress: int, message: str, **kwargs)
        
    Returns:
        str: Extracted text from the specified page range
    """
    def update_progress(progress, message, **kwargs):
        if callable(progress_callback):
            try:
                progress_callback(progress, message, **kwargs)
            except Exception as e:
                logger.warning(f"Error in PDF extraction progress callback: {str(e)}")
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        import time
        import io
        import os
        import tempfile
        from PyPDF2 import PdfReader
        
        logger.info(f"Starting PDF extraction with OCR: {use_ocr}")
        logger.info(f"File type: {type(uploaded_file)}")
        
        # Ensure we have a file-like object with seek capability
        if not hasattr(uploaded_file, 'read'):
            raise ValueError("Uploaded file is not a file-like object")
            
        # Reset file pointer
        if hasattr(uploaded_file, 'seek'):
            uploaded_file.seek(0)
            
        # Create a temporary file if needed
        temp_file = None
        if not hasattr(uploaded_file, 'name') or not os.path.exists(getattr(uploaded_file, 'name', '')):
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
            temp_file.write(uploaded_file.read())
            temp_file.close()
            file_path = temp_file.name
        else:
            file_path = uploaded_file.name
        
        # Try to extract text using PyPDF2 first
        def extract_with_pypdf(file_path):
            # Process the PDF in chunks to handle large files
            text_chunks = []
            
            # Get total number of pages
            with open(file_path, 'rb') as f:
                pdf_reader = PdfReader(f)
                total_pages = len(pdf_reader.pages)
                
                if end_page is None or end_page >= total_pages:
                    end_page = total_pages - 1
                else:
                    end_page = min(end_page, total_pages - 1)
                    
                # Report total pages found
                update_progress(10, f"Found {total_pages} pages in the document", 
                              status="Analyzing", total_pages=total_pages)
                
                # Process each chunk
                for chunk_start in range(start_page, end_page + 1, chunk_size):
                    chunk_end = min(chunk_start + chunk_size - 1, end_page)
                    current_page = chunk_start + 1
                    logger.info(f"Processing pages {current_page} to {chunk_end + 1} of {total_pages}")
                    
                    # Update progress
                    progress = 20 + int(60 * (chunk_start / max(total_pages, 1)))
                    update_progress(progress, 
                                  f"Processing page {current_page} of {total_pages}",
                                  status="Extracting Text",
                                  current_page=current_page,
                                  total_pages=total_pages)
                    
                    # Extract text from the chunk
                    chunk_text = ''
                    for page_num in range(chunk_start, chunk_end + 1):
                        page = pdf_reader.pages[page_num]
                        page_text = page.extract_text() or ''
                        chunk_text += page_text
                        
                        # Update progress for each page
                        current_page = page_num + 1
                        progress = 20 + int(60 * (current_page / max(total_pages, 1)))
                        update_progress(progress, 
                                      f"Processing page {current_page} of {total_pages}",
                                      status="Extracting Text",
                                      current_page=current_page,
                                      total_pages=total_pages)
                    
                    text_chunks.append(chunk_text)
                    
                    # Update progress after each chunk
                    progress = 20 + int(60 * ((chunk_end + 1) / max(total_pages, 1)))
                    update_progress(progress, 
                                  f"Processed up to page {chunk_end + 1} of {total_pages}",
                                  status="Processing",
                                  current_page=chunk_end + 1,
                                  total_pages=total_pages)
                
                # Join all chunks and return
                return "\n\n".join(text_chunks).strip()
        
        # Extract text using OCR (for image-based PDFs)
        def extract_text_with_ocr(pdf_path, start_page=0, end_page=None, progress_callback=None):
            """Extract text from PDF using OCR (Tesseract).
            
            Args:
                pdf_path: Path to the PDF file
                start_page: Page number to start from (0-based)
                end_page: Page number to end at (inclusive), None for all pages
                progress_callback: Callback function to report progress
            """
            def update_progress(progress, message, **kwargs):
                if callable(progress_callback):
                    try:
                        progress_callback(progress, message, **kwargs)
                    except Exception as e:
                        logger.warning(f"Error in OCR progress callback: {str(e)}")
            
            import tempfile
            import os
            from pdf2image import convert_from_path
            import pytesseract
            
            # Set Tesseract path if not in system PATH
            tesseract_path = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
            if os.name == 'nt' and os.path.exists(tesseract_path):
                pytesseract.pytesseract.tesseract_cmd = tesseract_path
            
            # Set Poppler path if not in system PATH
            poppler_path = None
            if os.name == 'nt':  # Windows
                poppler_path = r'C:\poppler-23.11.0\Library\bin'
                
            # Validate Tesseract installation
            try:
                pytesseract.get_tesseract_version()
            except pytesseract.TesseractNotFoundError:
                error_msg = f"Tesseract OCR not found at {tesseract_path}. Please install Tesseract OCR and ensure it's in your system PATH."
                logger.error(error_msg)
                update_progress(100, error_msg, status="Error")
                raise Exception(error_msg)
            
            try:
                # Convert PDF to images
                update_progress(10, "Converting PDF to images for OCR...", status="Preparing OCR")
                
                # Create a temporary directory for image files
                with tempfile.TemporaryDirectory() as temp_img_dir:
                    # Convert PDF to images with better quality settings
                    images = convert_from_path(
                        pdf_path,
                        first_page=start_page + 1,
                        last_page=end_page + 1 if end_page is not None else None,
                        poppler_path=poppler_path,
                        output_folder=temp_img_dir,
                        fmt='png',
                        dpi=300,
                        thread_count=2,
                        grayscale=True
                    )
                    
                    if not images:
                        error_msg = "No images were generated from the PDF. The PDF might be corrupted or empty."
                        logger.error(error_msg)
                        update_progress(100, error_msg, status="Error")
                        return ""
                    
                    total_pages = len(images)
                    update_progress(20, f"Processing {total_pages} pages with OCR...", 
                                  status="Running OCR", total_pages=total_pages)
                    
                    # Extract text from each image
                    text = []
                    for i, image in enumerate(images, start=start_page):
                        try:
                            # Calculate progress (20-90% for OCR processing)
                            progress = 20 + int(70 * ((i - start_page + 1) / total_pages))
                            update_progress(progress, 
                                          f"Processing page {i + 1} of {start_page + total_pages} with OCR...",
                                          status="Running OCR",
                                          current_page=i + 1,
                                          total_pages=start_page + total_pages)
                            
                            # Preprocess image for better OCR results
                            # Convert to grayscale if not already
                            if image.mode != 'L':
                                image = image.convert('L')
                            
                            # Enhance contrast
                            from PIL import ImageEnhance
                            enhancer = ImageEnhance.Contrast(image)
                            image = enhancer.enhance(2.0)  # Increase contrast
                            
                            # Run OCR with optimized settings for Arabic text
                            page_text = pytesseract.image_to_string(
                                image, 
                                lang='ara',
                                config='--psm 6 --oem 3 -c preserve_interword_spaces=1'
                            )
                            
                            if page_text.strip():
                                text.append(page_text)
                                logger.info(f"Processed page {i + 1} with OCR, extracted {len(page_text)} characters")
                            else:
                                logger.warning(f"No text found on page {i + 1} with OCR")
                                
                        except Exception as e:
                            logger.error(f"Error processing page {i + 1} with OCR: {str(e)}")
                            continue
                    
                    if not text:
                        error_msg = "OCR processing completed but no text was extracted from any page."
                        logger.error(error_msg)
                        update_progress(100, error_msg, status="Error")
                        return ""
                    
                    update_progress(95, "OCR processing completed, finalizing text...", status="Finalizing")
                    
                    # Join all page texts with page breaks
                    result_text = "\n\n".join(text)
                    logger.info(f"OCR processing completed. Extracted {len(result_text)} characters in total.")
                    
                    return result_text
                    
            except Exception as e:
                error_msg = f"Error during OCR processing: {str(e)}"
                logger.error(error_msg, exc_info=True)
                update_progress(100, error_msg, status="Error")
                raise Exception(error_msg)
        
        # Start processing
        start_time = time.time()
        
        try:
            # First try standard text extraction if not forcing OCR
            if not use_ocr:
                try:
                    update_progress(5, "Starting text extraction...", status="Starting")
                    text = extract_with_pypdf(file_path)
                    if text and text.strip():
                        logger.info("Text extraction completed successfully")
                        update_progress(100, "Extraction completed successfully", status="Completed")
                        return text
                    logger.warning("No text found with standard extraction, falling back to OCR...")
                    update_progress(30, "No text found, switching to OCR...", status="Using OCR")
                    text = extract_text_with_ocr(file_path, start_page, end_page, progress_callback=progress_callback)
                except Exception as e:
                    logger.warning(f"Standard extraction failed: {str(e)}, falling back to OCR...")
                    update_progress(30, f"Standard extraction failed: {str(e)[:100]}... Trying OCR...", status="Using OCR")
                    text = extract_text_with_ocr(file_path, start_page, end_page, progress_callback=progress_callback)
            else:
                update_progress(5, "Starting OCR processing...", status="Starting OCR")
                text = extract_text_with_ocr(file_path, start_page, end_page, progress_callback=progress_callback)
            
            if not text or not text.strip():
                error_msg = "No text could be extracted from the PDF. The PDF might be encrypted, image-based with poor quality, or contain no recognizable text."
                update_progress(100, error_msg, status="Error")
                raise Exception(error_msg)
                
            update_progress(100, "Text extraction completed successfully", status="Completed")
            return text
            
        except Exception as e:
            error_msg = f"Error processing PDF: {str(e)}"
            logger.error(error_msg, exc_info=True)
            update_progress(100, error_msg, status="Error")
            raise Exception(error_msg)
        
        finally:
            # Clean up temporary file if we created one
            if temp_file and os.path.exists(temp_file.name):
                try:
                    os.unlink(temp_file.name)
                    logger.debug("Cleaned up temporary file")
                except Exception as e:
                    logger.warning(f"Error cleaning up temporary file: {str(e)}")
        
    except Exception as e:
        error_msg = f"Failed to extract text from PDF: {str(e)}"
        print(error_msg)
        raise Exception(_(error_msg))


def extract_text_from_docx(uploaded_file):
    """Extract text from a DOCX file."""
    try:
        doc = DocxDocument(BytesIO(uploaded_file.read()))
        return "\n".join([paragraph.text for paragraph in doc.paragraphs])
    except Exception as e:
        raise Exception(_("Failed to extract text from Word document: %s") % str(e))


def extract_hadiths(text):
    """Extract hadiths from text using regex patterns."""
    # Common hadith patterns
    hadith_patterns = [
        r'حَدَّثَنَا.*?[.،]',  # حدثنا pattern
        r'أَخْبَرَنَا.*?[.،]',  # أخبرنا pattern
        r'عَنْ.*?[.،]',  # عن pattern
        r'قَالَ رَسُولُ اللَّهِ.*?[.،]',  # قال رسول الله pattern
    ]
    
    hadiths = []
    for pattern in hadith_patterns:
        matches = re.finditer(pattern, text, re.DOTALL)
        for match in matches:
            hadith = match.group(0).strip()
            if hadith not in hadiths:  # Avoid duplicates
                hadiths.append(hadith)
    
    return hadiths


def extract_narrators(hadith_text):
    """Extract narrators from hadith text."""
    # Common narrator patterns in Arabic
    narrator_patterns = [
        r'حَدَّثَنَا\s+(\S+)(?:\s+\S+){0,2}(?=\s+عَنْ|\s+قَالَ|\s+أن|$)',
        r'عَنْ\s+(\S+)(?:\s+\S+){0,2}(?=\s+عَنْ|\s+قَالَ|\s+أن|$)',
        r'أَخْبَرَنَا\s+(\S+)(?:\s+\S+){0,2}(?=\s+عَنْ|\s+قَالَ|\s+أن|$)',
    ]
    
    narrators = []
    for pattern in narrator_patterns:
        matches = re.finditer(pattern, hadith_text)
        for match in matches:
            narrator = match.group(1).strip()
            if narrator not in narrators:  # Avoid duplicates
                narrators.append(narrator)
    
    return narrators


import logging
import traceback
from django.utils.translation import gettext_lazy as _

def process_document(document, max_pages=None, chunk_size=10, progress_callback=None):
    """Process a document and extract hadiths and narrators.
    
    Args:
        document: The document model instance
        max_pages: Maximum number of pages to process (for testing with large documents)
        chunk_size: Number of pages to process at a time (for large documents)
        progress_callback: Callback function to report progress (progress: int, message: str, **kwargs)
    
    Returns:
        dict: {
            'success': bool,
            'hadiths': list of dicts (if successful),
            'total_hadiths': int,
            'error': str (if failed)
        }
    """
    logger = logging.getLogger(__name__)
    
    def update_progress(progress, message, **kwargs):
        """Helper to update progress with consistent formatting."""
        if callable(progress_callback):
            try:
                # Ensure progress is between 0-100
                progress = max(0, min(100, int(progress)))
                progress_callback(progress, str(message), **kwargs)
            except Exception as e:
                logger.warning(f"Error in progress callback: {str(e)}")
    
    try:
        logger = logging.getLogger(__name__)
        logger.info(f"Processing document: {document.title}, ID: {document.id}")
        
        # Get the file content
        file = document.file
        file_extension = document.get_file_extension().lower()
        
        # Log file info
        file_info = {
            'name': file.name,
            'size': f"{file.size/1024/1024:.2f}MB" if hasattr(file, 'size') else 'unknown',
            'extension': file_extension,
            'path': file.path if hasattr(file, 'path') else 'In-memory file'
        }
        logger.info(f"Processing file: {file_info}")
        update_progress(5, "Analyzing document...", status="Analyzing")
        
        # For large PDFs, we'll process them in chunks
        is_large_file = file_extension == 'pdf' and (hasattr(file, 'size') and file.size > 20 * 1024 * 1024)  # > 20MB
        if is_large_file:
            logger.warning(f"Large PDF detected ({file_info['size']}), processing in chunks of {chunk_size} pages...")
        
        # Extract text based on file type
        text = ""
        if file_extension == 'pdf':
            logger.info("Extracting text from PDF file")
            update_progress(10, "Preparing PDF for extraction...", status="Preparing")
            
            # For large files, process in smaller chunks
            if is_large_file:
                logger.info(f"Processing large PDF in chunks of {chunk_size} pages...")
                update_progress(15, f"Processing large PDF in chunks of {chunk_size} pages...", status="Processing")
                
                # First try without OCR, then fall back to OCR if needed
                try:
                    update_progress(20, "Extracting text from PDF (standard method)...", status="Extracting Text")
                    text = extract_text_from_pdf(file, chunk_size=chunk_size, use_ocr=False, progress_callback=progress_callback)
                    if not text.strip():
                        logger.warning("Standard extraction failed, trying with OCR...")
                        update_progress(30, "Standard extraction failed, trying with OCR...", status="Using OCR")
                        text = extract_text_from_pdf(file, chunk_size=chunk_size, use_ocr=True, progress_callback=progress_callback)
                except Exception as e:
                    logger.warning(f"Error in standard extraction: {str(e)}, trying with OCR...")
                    update_progress(30, f"Error in extraction: {str(e)[:100]}... Trying OCR...", status="Using OCR")
                    text = extract_text_from_pdf(file, chunk_size=chunk_size, use_ocr=True, progress_callback=progress_callback)
            else:
                # Try standard extraction first, then fall back to OCR if needed
                update_progress(20, "Extracting text from PDF (standard method)...", status="Extracting Text")
                try:
                    text = extract_text_from_pdf(file, use_ocr=False, progress_callback=progress_callback)
                    if not text.strip():
                        logger.warning("Standard extraction failed, trying with OCR...")
                        update_progress(30, "Standard extraction failed, trying with OCR...", status="Using OCR")
                        text = extract_text_from_pdf(file, use_ocr=True, progress_callback=progress_callback)
                except Exception as e:
                    logger.warning(f"Error in standard extraction: {str(e)}, trying with OCR...")
                    update_progress(30, f"Error in extraction: {str(e)[:100]}... Trying OCR...", status="Using OCR")
                    text = extract_text_from_pdf(file, use_ocr=True, progress_callback=progress_callback)
        elif file_extension in ['doc', 'docx']:
            logger.info("Extracting text from Word document")
            update_progress(30, "Extracting text from Word document...", status="Extracting Text")
            try:
                text = extract_text_from_docx(file)
                update_progress(70, "Text extraction complete", status="Processing")
            except Exception as e:
                error_msg = f"Error extracting text from Word document: {str(e)}"
                logger.error(error_msg, exc_info=True)
                return {'success': False, 'error': error_msg}
        else:
            error_msg = f"Unsupported file format: {file_extension}"
            logger.error(error_msg)
            return {'success': False, 'error': error_msg}
        
        # Check if we got any text
        if not text or not text.strip():
            error_msg = "No text could be extracted from the document"
            logger.error(error_msg)
            return {'success': False, 'error': error_msg}
        
        # Extract hadiths
        logger.info("Extracting hadiths from text...")
        update_progress(80, "Extracting hadiths...", status="Processing")
        try:
            hadiths = extract_hadiths(text)
            logger.info(f"Found {len(hadiths)} potential hadiths")
            
            # Extract narrators for each hadith
            results = []
            total_hadiths = len(hadiths)
            for i, hadith in enumerate(hadiths, 1):
                progress = 80 + int(15 * (i / max(1, total_hadiths)))  # 80-95%
                update_progress(progress, f"Processing hadith {i} of {total_hadiths}...", 
                              status="Processing", current_hadith=i, total_hadiths=total_hadiths)
                
                narrators = extract_narrators(hadith)
                results.append({
                    'hadith': hadith,
                    'narrators': narrators,
                    'position': i,
                    'length': len(hadith)
                })
            
            # Final update
            update_progress(100, f"Successfully extracted {len(results)} hadiths", 
                          status="Completed", total_hadiths=len(results))
            
            return {
                'success': True,
                'hadiths': results,
                'total_hadiths': len(results)
            }
            
        except Exception as e:
            error_msg = f"Error extracting hadiths: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {'success': False, 'error': error_msg}
            
    except Exception as e:
        error_msg = f"Error processing document: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {'success': False, 'error': error_msg}

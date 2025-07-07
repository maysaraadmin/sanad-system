import os
import logging
import fitz  # PyMuPDF
from django.conf import settings
from PIL import Image
import io
import base64

logger = logging.getLogger(__name__)

def validate_pdf_file(pdf_path):
    """Validate that the PDF file exists and is accessible"""
    if not os.path.exists(pdf_path):
        error_msg = f"PDF file not found: {pdf_path}"
        logger.error(error_msg)
        raise FileNotFoundError(error_msg)
    
    if not os.path.isfile(pdf_path):
        error_msg = f"Path is not a file: {pdf_path}"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    if os.path.getsize(pdf_path) == 0:
        error_msg = f"PDF file is empty: {pdf_path}"
        logger.error(error_msg)
        raise ValueError(error_msg)

def render_pdf_page_to_image(pdf_path, page_number=0, zoom=1.0):
    """
    Render a PDF page to a base64-encoded image
    
    Args:
        pdf_path: Path to the PDF file
        page_number: 0-based page number
        zoom: Zoom level (1.0 = 100%)
        
    Returns:
        dict: {
            'image': base64-encoded image data,
            'width': image width,
            'height': image height,
            'total_pages': total pages in document,
            'current_page': 1-based page number
        }
        
    Raises:
        FileNotFoundError: If the PDF file doesn't exist
        ValueError: If the PDF is invalid or page number is out of range
        Exception: For other rendering errors
    """
    # Input validation
    validate_pdf_file(pdf_path)
    
    # Initialize variables
    doc = None
    
    try:
        # Open the PDF document
        try:
            doc = fitz.open(pdf_path)
            total_pages = len(doc)
            
            if page_number < 0 or page_number >= total_pages:
                raise ValueError(f"Page number {page_number} is out of range (0-{total_pages-1})")
                
        except RuntimeError as e:
            logger.error(f"Failed to open PDF: {str(e)}")
            raise ValueError(f"The file is not a valid PDF or is corrupted: {str(e)}")
        
        # Load the requested page
        try:
            page = doc.load_page(page_number)
        except Exception as e:
            logger.error(f"Failed to load page {page_number}: {str(e)}")
            raise ValueError(f"Failed to load page {page_number}: {str(e)}")
        
        # Set zoom level with bounds checking
        try:
            zoom = max(0.25, min(3.0, float(zoom)))  # Clamp zoom between 0.25 and 3.0
            mat = fitz.Matrix(zoom, zoom)
        except (TypeError, ValueError) as e:
            logger.warning(f"Invalid zoom level {zoom}, using default 1.0: {str(e)}")
            mat = fitz.Matrix(1.0, 1.0)
        
        # Render the page to an image
        try:
            # Use anti-aliasing for better quality
            pix = page.get_pixmap(
                matrix=mat,
                alpha=False,
                dpi=150,  # Higher DPI for better quality
                colorspace='rgb',
                clip=None,
                annots=True  # Include annotations
            )
            
            # Convert to PNG
            img_data = pix.tobytes('png')
            img_str = base64.b64encode(img_data).decode('utf-8')
            
            return {
                'image': f"data:image/png;base64,{img_str}",
                'width': pix.width,
                'height': pix.height,
                'total_pages': total_pages,
                'current_page': page_number + 1  # Convert to 1-based for display
            }
            
        except Exception as e:
            error_msg = f"Error rendering PDF page {page_number}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise Exception(f"Failed to render PDF page: {str(e)}")
            
    except Exception as e:
        # Log the error and re-raise
        logger.error(f"Error in render_pdf_page_to_image: {str(e)}", exc_info=True)
        raise
        
    finally:
        # Ensure the document is always properly closed
        if doc is not None:
            try:
                doc.close()
            except Exception as e:
                logger.warning(f"Error closing PDF document: {str(e)}")

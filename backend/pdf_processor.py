import os
import tempfile
from typing import List
import fitz  # PyMuPDF


class PDFProcessor:
    """Process PDF files - convert pages to images for OCR"""
    
    def __init__(self, dpi: int = 200):
        """
        Initialize PDF processor
        
        Args:
            dpi: Resolution for image conversion (default 200)
        """
        self.dpi = dpi
        self.zoom = dpi / 72  # 72 is the default PDF resolution
    
    def pdf_to_images(self, pdf_path: str, output_dir: str = None) -> List[str]:
        """
        Convert PDF pages to images
        
        Args:
            pdf_path: Path to the PDF file
            output_dir: Directory to save images (default: temp directory)
        
        Returns:
            List of paths to generated images
        """
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        # Use temp directory if output_dir not specified
        if output_dir is None:
            output_dir = tempfile.gettempdir()
        
        os.makedirs(output_dir, exist_ok=True)
        
        image_paths = []
        
        try:
            # Open the PDF
            doc = fitz.open(pdf_path)
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                
                # Create transformation matrix for desired resolution
                mat = fitz.Matrix(self.zoom, self.zoom)
                
                # Render page to pixmap (image)
                pix = page.get_pixmap(matrix=mat)
                
                # Generate unique filename
                base_name = os.path.splitext(os.path.basename(pdf_path))[0]
                image_filename = f"{base_name}_page_{page_num + 1}.png"
                image_path = os.path.join(output_dir, image_filename)
                
                # Save as PNG
                pix.save(image_path)
                image_paths.append(image_path)
            
            doc.close()
            
        except Exception as e:
            print(f"Error converting PDF to images: {e}")
            raise
        
        return image_paths
    
    def get_page_count(self, pdf_path: str) -> int:
        """
        Get the number of pages in a PDF
        
        Args:
            pdf_path: Path to the PDF file
        
        Returns:
            Number of pages
        """
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        try:
            doc = fitz.open(pdf_path)
            count = len(doc)
            doc.close()
            return count
        except Exception as e:
            print(f"Error getting page count: {e}")
            raise
    
    def extract_text_direct(self, pdf_path: str) -> str:
        """
        Extract text directly from PDF (without OCR)
        Useful for text-based PDFs
        
        Args:
            pdf_path: Path to the PDF file
        
        Returns:
            Extracted text from all pages
        """
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        all_text = []
        
        try:
            doc = fitz.open(pdf_path)
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text()
                if text.strip():
                    all_text.append(f"--- Page {page_num + 1} ---\n{text}")
            
            doc.close()
            
        except Exception as e:
            print(f"Error extracting text from PDF: {e}")
            raise
        
        return "\n\n".join(all_text)
    
    def is_scanned_pdf(self, pdf_path: str) -> bool:
        """
        Check if PDF is scanned (image-based) or text-based
        
        Args:
            pdf_path: Path to the PDF file
        
        Returns:
            True if PDF appears to be scanned/image-based
        """
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        try:
            doc = fitz.open(pdf_path)
            
            total_text_length = 0
            total_pages = len(doc)
            
            for page_num in range(min(3, total_pages)):  # Check first 3 pages
                page = doc[page_num]
                text = page.get_text()
                total_text_length += len(text.strip())
            
            doc.close()
            
            # If average text per page is very low, it's likely scanned
            avg_text_per_page = total_text_length / min(3, total_pages)
            return avg_text_per_page < 100
            
        except Exception as e:
            print(f"Error checking PDF type: {e}")
            return True  # Assume scanned if can't determine
    
    def pdf_to_single_image(self, pdf_path: str, page_num: int = 0, output_path: str = None) -> str:
        """
        Convert a single PDF page to image
        
        Args:
            pdf_path: Path to the PDF file
            page_num: Page number to convert (0-indexed)
            output_path: Path for output image (default: temp file)
        
        Returns:
            Path to generated image
        """
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        try:
            doc = fitz.open(pdf_path)
            
            if page_num >= len(doc):
                raise ValueError(f"Page {page_num} does not exist. PDF has {len(doc)} pages.")
            
            page = doc[page_num]
            mat = fitz.Matrix(self.zoom, self.zoom)
            pix = page.get_pixmap(matrix=mat)
            
            if output_path is None:
                fd, output_path = tempfile.mkstemp(suffix='.png')
                os.close(fd)
            
            pix.save(output_path)
            doc.close()
            
            return output_path
            
        except Exception as e:
            print(f"Error converting PDF page to image: {e}")
            raise

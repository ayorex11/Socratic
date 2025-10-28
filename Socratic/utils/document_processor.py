import PyPDF2
import pytesseract
from PIL import Image
import os
import re
from docx import Document

class DocumentProcessor:
    """
    Enhanced text extraction with comprehensive structural analysis
    """
    
    @staticmethod
    def extract_text_from_pdf(file_path):
        """Extract coherent text from PDF with structural preservation"""
        try:
            with open(file_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                full_text = ""
                
                # Extract text from all pages
                for page_num, page in enumerate(reader.pages):
                    page_text = page.extract_text()
                    if page_text:
                        full_text += page_text + "\n"
                
                # Reconstruct paragraphs and filter non-content
                processed_text = DocumentProcessor._reconstruct_paragraphs(full_text)
                meaningful_content = DocumentProcessor._extract_meaningful_sections(processed_text)
                print(meaningful_content)
                
                return meaningful_content.strip()
                
        except Exception as e:
            raise Exception(f"PDF extraction failed: {str(e)}")
    
    @staticmethod
    def _extract_meaningful_sections(text):
        """Extract meaningful sections while preserving document structure"""
        if not text:
            return ""
        
        lines = text.split('\n')
        sections = []
        current_section = []
        current_header = None
        in_toc = False
        
        # Comprehensive patterns for section headers
        header_patterns = [
            # Unit patterns
            r'^UNIT\s+\d+',
            r'^Unit\s+\d+',
            # Chapter patterns
            r'^CHAPTER\s+\d+',
            r'^Chapter\s+\d+',
            r'^CH\.?\s*\d+',
            # Numbered sections (1, 1.1, 1.1.1, etc.)
            r'^\d+\.\d+(\.\d+)*\s+[A-Za-z]',
            r'^\d+\.\s+[A-Za-z]',
            r'^\d+\s+[A-Za-z]',
            # Roman numerals
            r'^(I|II|III|IV|V|VI|VII|VIII|IX|X|XI|XII)\.?\s+[A-Za-z]',
            r'^(i|ii|iii|iv|v|vi|vii|viii|ix|x|xi|xii)\.?\s+[A-Za-z]',
            # Lettered sections (A, B, C, etc.)
            r'^[A-Z]\.\s+[A-Za-z]',
            r'^[a-z]\.\s+[A-Za-z]',
            # Substantial title lines (multiple words, proper capitalization)
            r'^[A-Z][A-Za-z]+(\s+[A-Za-z]+){2,}.*$',
            # ALL CAPS meaningful headers (but not too short)
            r'^[A-Z][A-Z\s]{10,}$',
        ]
        
        # TOC detection patterns
        toc_patterns = [
            r'contents?|table of contents?|index',
            r'^\s*(page|pg\.?)\s*\d+',
            r'\.\.\.\s*\d+$'
        ]
        
        # Clear non-content patterns
        non_content_patterns = [
            r'^\.\.\.\s*\d+$', r'^\d+\s*$', r'^page\s+\d+', r'^pg\.?\s*\d+',
            r'^copyright', r'^confidential', r'^\d+/\d+/\d+', r'^version\s+\d',
            r'^=====', r'^\*\*\*\*\*', r'^------', r'^–––––',  # Page separators
            r'^figure\s+\d+', r'^table\s+\d+', r'^fig\.\s*\d+',  # Figure/table captions
        ]
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check for TOC start
            if re.search(r'contents?|table of contents?|index', line, re.IGNORECASE):
                in_toc = True
                continue
            
            # Skip TOC content
            if in_toc:
                if DocumentProcessor._is_toc_line(line):
                    continue
                else:
                    # If we find substantial non-TOC content, exit TOC
                    if len(line) > 50 and not DocumentProcessor._is_toc_line(line):
                        in_toc = False
                    else:
                        continue
            
            # Skip clear non-content
            if any(re.search(pattern, line, re.IGNORECASE) for pattern in non_content_patterns):
                continue
            
            # Check if this is a section header
            is_header = any(re.search(pattern, line) for pattern in header_patterns)
            
            if is_header:
                # Save previous section if meaningful
                if current_section and DocumentProcessor._is_meaningful_section(current_section):
                    if current_header:
                        sections.append(f"{current_header}\n{''.join(current_section)}")
                    else:
                        sections.append(''.join(current_section))
                
                # Start new section
                current_header = line
                current_section = []
            else:
                # Add content line if meaningful
                if DocumentProcessor._is_meaningful_line(line):
                    current_section.append(line + " ")
        
        # Add final section
        if current_section and DocumentProcessor._is_meaningful_section(current_section):
            if current_header:
                sections.append(f"{current_header}\n{''.join(current_section)}")
            else:
                sections.append(''.join(current_section))
        
        return '\n\n'.join(sections)
    
    @staticmethod
    def _is_toc_line(line):
        """Check if line is part of table of contents"""
        toc_indicators = [
            r'\.\.\.\s*\d+$',
            r'^\d+\.\d*\s',
            r'^\s*\w+\s+\.\.\.\s*\d+',
            r'^page\s+\d+',
            r'^\d+\s*$'
        ]
        return any(re.search(pattern, line, re.IGNORECASE) for pattern in toc_indicators)
    
    @staticmethod
    def _is_meaningful_section(section_lines):
        """Determine if a section contains meaningful content"""
        if not section_lines:
            return False
        
        section_text = ' '.join(section_lines)
        
        # Minimum length requirement
        if len(section_text) < 40:
            return False
        
        # Check for sentence structure
        sentences = re.split(r'[.!?]+', section_text)
        if len(sentences) < 1:
            return False
        
        # Check word count and diversity
        words = section_text.split()
        if len(words) < 10:
            return False
        
        # Check for content indicators (broad technical/academic terms)
        content_indicators = [
            # Technical terms
            'network', 'control', 'data', 'plane', 'application', 'software',
            'security', 'management', 'traditional', 'protocol', 'switch',
            'router', 'virtual', 'hardware', 'system', 'architecture',
            # Academic/document terms
            'introduction', 'background', 'method', 'result', 'analysis',
            'conclusion', 'discussion', 'example', 'definition', 'theory',
            'model', 'framework', 'implementation', 'evaluation'
        ]
        
        lower_text = section_text.lower()
        content_matches = sum(1 for indicator in content_indicators if indicator in lower_text)
        
        # For academic/technical documents, require at least 1 content indicator
        return content_matches >= 1
    
    @staticmethod
    def _is_meaningful_line(line):
        """Check if a single line contains meaningful content"""
        if len(line) < 15:
            return False
        
        # Skip lines that are entirely uppercase (unless they're reasonable headers)
        if line.isupper() and len(line) < 80:
            return False
        
        # Check alpha character ratio
        alpha_chars = sum(1 for c in line if c.isalpha())
        if alpha_chars / len(line) < 0.3:
            return False
        
        # Skip lines that look like references or captions
        reference_patterns = [
            r'^(Figure|Table|Fig\.|Table|Equation)\s+\d+',
            r'^\[\d+\]',  # Citation
            r'^References?$',
            r'^Bibliography$'
        ]
        
        if any(re.search(pattern, line, re.IGNORECASE) for pattern in reference_patterns):
            return False
        
        return True
    
    @staticmethod
    def _reconstruct_paragraphs(text):
        """Reconstruct proper paragraphs from fragmented text"""
        if not text:
            return ""
        
        # Normalize line endings
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        
        # Join hyphenated words across lines
        text = re.sub(r'(\w+)-\n(\w+)', r'\1\2', text)
        
        # Split into lines and process
        lines = text.split('\n')
        reconstructed_lines = []
        current_paragraph = []
        
        for line in lines:
            line = line.strip()
            if not line:
                if current_paragraph:
                    reconstructed_lines.append(' '.join(current_paragraph))
                    current_paragraph = []
                continue
            
            # Check if this line starts a new paragraph
            if (current_paragraph and 
                re.match(r'^[A-Z"\(\[\-]', line) and 
                current_paragraph[-1].endswith(('.', ':",', ';', '))'))):
                reconstructed_lines.append(' '.join(current_paragraph))
                current_paragraph = [line]
            else:
                current_paragraph.append(line)
        
        if current_paragraph:
            reconstructed_lines.append(' '.join(current_paragraph))
        
        return '\n'.join(reconstructed_lines)
    
    @staticmethod
    def extract_text_from_docx(file_path):
        """Extract text from Word documents with structural preservation"""
        try:
            doc = Document(file_path)
            full_text = ""
            
            for paragraph in doc.paragraphs:
                para_text = paragraph.text.strip()
                if para_text and DocumentProcessor._is_meaningful_line(para_text):
                    full_text += para_text + "\n"
            
            # Process with same section extraction as PDF
            processed_text = DocumentProcessor._reconstruct_paragraphs(full_text)
            meaningful_content = DocumentProcessor._extract_meaningful_sections(processed_text)
            
            return meaningful_content.strip()
            
        except Exception as e:
            raise Exception(f"DOCX extraction failed: {str(e)}")
    
    @staticmethod
    def extract_text_from_image(file_path):
        """Extract text from images using OCR"""
        try:
            image = Image.open(file_path)
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            text = pytesseract.image_to_string(image)
            
            # Process with same section extraction
            processed_text = DocumentProcessor._reconstruct_paragraphs(text)
            meaningful_content = DocumentProcessor._extract_meaningful_sections(processed_text)
            print(f'this is past questions {meaningful_content}')
            
            return meaningful_content.strip()
            
        except Exception as e:
            raise Exception(f"Image OCR failed: {str(e)}. Please ensure the image is clear and well-lit.")
    
    @staticmethod
    def extract_text(file_path, file_type):
        """Extract text from file with meaningful content preservation"""
        file_type = file_type.upper()
        
        if file_type in ['PDF']:
            return DocumentProcessor.extract_text_from_pdf(file_path)
        elif file_type in ['DOCX', 'DOC']:
            return DocumentProcessor.extract_text_from_docx(file_path)
        elif file_type in ['JPG', 'JPEG', 'PNG', 'BMP', 'TIFF']:
            return DocumentProcessor.extract_text_from_image(file_path)
        else:
            raise ValueError(f"Unsupported file type: {file_type}")
    
    @staticmethod
    def get_file_type(filename):
        """Determine file type from filename"""
        ext = os.path.splitext(filename)[1].lower().replace('.', '')
        return ext.upper()

    @staticmethod
    def analyze_content_quality(text):
        """Analyze if the extracted content is meaningful"""
        if not text:
            return False, "No text extracted"
        
        lines = text.split('\n')
        substantial_lines = [line for line in lines if len(line.strip()) > 30]
        
        if len(substantial_lines) < 3:
            return False, "Insufficient substantial content"
        
        # Count various section types
        unit_sections = re.findall(r'^UNIT\s+\d+', text, re.MULTILINE | re.IGNORECASE)
        chapter_sections = re.findall(r'^CHAPTER\s+\d+', text, re.MULTILINE | re.IGNORECASE)
        numbered_sections = re.findall(r'^\d+\.\d+\s+', text, re.MULTILINE)
        
        total_sections = len(unit_sections) + len(chapter_sections) + len(numbered_sections)
        
        total_chars = len(text)
        return True, f"Content quality OK: {len(substantial_lines)} substantial lines, {total_sections} sections, {total_chars} characters"

    @staticmethod
    def get_content_stats(text):
        """Get detailed statistics about extracted content"""
        if not text:
            return "No content"
        
        lines = text.split('\n')
        
        # Find various section types
        unit_sections = re.findall(r'^UNIT\s+\d+.*', text, re.MULTILINE | re.IGNORECASE)
        chapter_sections = re.findall(r'^CHAPTER\s+\d+.*', text, re.MULTILINE | re.IGNORECASE)
        numbered_sections = re.findall(r'^\d+\.\d+.*', text, re.MULTILINE)
        roman_sections = re.findall(r'^(I|II|III|IV|V|VI|VII|VIII|IX|X)\.?.*', text, re.MULTILINE)
        
        all_sections = unit_sections + chapter_sections + numbered_sections + roman_sections
        
        stats = {
            'total_characters': len(text),
            'total_lines': len(lines),
            'total_sections': len(all_sections),
            'unit_sections': len(unit_sections),
            'chapter_sections': len(chapter_sections),
            'numbered_sections': len(numbered_sections),
            'roman_sections': len(roman_sections),
            'section_examples': all_sections[:8]  # First 8 sections found
        }
        
        return stats

    @staticmethod
    def debug_extraction(file_path, file_type='PDF'):
        """Debug method to see what's being extracted at each stage"""
        print("=== DOCUMENT EXTRACTION DEBUG ===")
        
        # Raw extraction
        if file_type.upper() == 'PDF':
            with open(file_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                raw_text = ""
                for page in reader.pages:
                    raw_text += page.extract_text() + "\n"
        else:
            raw_text = "Debug available for PDF only"
        
        print(f"1. RAW TEXT LENGTH: {len(raw_text)}")
        print("RAW TEXT SAMPLE (first 500 chars):")
        print(raw_text[:500])
        print("\n" + "="*50)
        
        # After reconstruction
        reconstructed = DocumentProcessor._reconstruct_paragraphs(raw_text)
        print(f"2. RECONSTRUCTED LENGTH: {len(reconstructed)}")
        print("RECONSTRUCTED SAMPLE:")
        print(reconstructed[:500])
        print("\n" + "="*50)
        
        # Final output
        final = DocumentProcessor.extract_text(file_path, file_type)
        print(f"3. FINAL EXTRACTED LENGTH: {len(final)}")
        print("FINAL CONTENT SAMPLE:")
        print(final[:1000])
        
        return final
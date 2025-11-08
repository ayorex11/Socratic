from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_LEFT, TA_JUSTIFY, TA_CENTER
from reportlab.lib import colors
import re
from django.core.files.storage import default_storage
from io import BytesIO

class PDFGenerator:
    """
    Generates downloadable PDF reports directly to R2
    """
    
    @staticmethod
    def generate_report(processing_result, output_filename):
        """
        Generate a PDF report with summary and Q&A directly to R2
        """
        try:
            # Create PDF in memory
            buffer = BytesIO()
            
            # Create PDF document with better margins
            doc = SimpleDocTemplate(
                buffer,
                pagesize=letter,
                rightMargin=54,
                leftMargin=54,
                topMargin=72,
                bottomMargin=54
            )
            
            # Create custom styles
            styles = getSampleStyleSheet()
            
            # Title style - GREEN
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=16,
                spaceAfter=20,
                alignment=TA_CENTER,
                textColor='#1e7e34'  # Green
            )
            
            # Main heading style - GREEN
            heading_style = ParagraphStyle(
                'CustomHeading',
                parent=styles['Heading2'],
                fontSize=14,
                spaceBefore=20,
                spaceAfter=10,
                alignment=TA_LEFT,
                textColor='#28a745'  # Green
            )
            
            # Subheading style (for ### headings) - GREEN
            subheading_style = ParagraphStyle(
                'SubHeading',
                parent=styles['Heading3'],
                fontSize=12,
                spaceBefore=15,
                spaceAfter=8,
                alignment=TA_LEFT,
                textColor='#1e7e34',  # Green
                fontName='Helvetica-Bold'
            )
            
            # Normal text style
            normal_style = ParagraphStyle(
                'CustomBody',
                parent=styles['BodyText'],
                fontSize=10,
                leading=13,
                alignment=TA_JUSTIFY,
                spaceAfter=8
            )
            
            # Bullet point style
            bullet_style = ParagraphStyle(
                'BulletText',
                parent=styles['BodyText'],
                fontSize=10,
                leading=13,
                alignment=TA_JUSTIFY,
                leftIndent=20,
                spaceAfter=4
            )
            
            # Question style - GREEN
            question_style = ParagraphStyle(
                'QuestionStyle',
                parent=styles['BodyText'],
                fontSize=11,
                leading=14,
                spaceBefore=12,
                spaceAfter=6,
                fontName='Helvetica-Bold',
                textColor='#1e7e34',  # Green
                leftIndent=0
            )
            
            # Answer style
            answer_style = ParagraphStyle(
                'AnswerStyle',
                parent=styles['BodyText'],
                fontSize=10,
                leading=13,
                leftIndent=10,
                spaceAfter=12,
                alignment=TA_JUSTIFY
            )
            
            # Footer style
            footer_style = ParagraphStyle(
                'FooterStyle',
                parent=styles['BodyText'],
                fontSize=10,
                alignment=TA_CENTER,
                textColor='#6c757d',
                fontName='Helvetica-Oblique',
                spaceBefore=30
            )
            
            # Content
            story = []
            
            # Title
            title = Paragraph(f"Study Report: {processing_result.document_title}", title_style)
            story.append(title)
            story.append(Spacer(1, 0.2 * inch))
            
            # Context info
            if processing_result.used_past_questions:
                context_info = Paragraph("<b>Context:</b> Generated with past exam questions context", normal_style)
            else:
                context_info = Paragraph("<b>Context:</b> General study material", normal_style)
            story.append(context_info)
            story.append(Spacer(1, 0.3 * inch))
            
            # Summary section
            summary_title = Paragraph("Summary", heading_style)
            story.append(summary_title)
            
            # Process and format summary text with markdown parsing
            summary_text = processing_result.summary
            formatted_summary = PDFGenerator.parse_markdown_text(summary_text, normal_style, bullet_style, subheading_style)
            
            for element in formatted_summary:
                story.append(element)
            
            story.append(Spacer(1, 0.3 * inch))
            
            # Questions & Answers section
            qa_title = Paragraph("Practice Questions & Answers", heading_style)
            story.append(qa_title)
            story.append(Spacer(1, 0.2 * inch))
            
            qa_data = processing_result.questions_answers
            if 'qa_pairs' in qa_data:
                for qa in qa_data['qa_pairs']:
                    # Clean and format question
                    clean_question = PDFGenerator.clean_text(qa['question'])
                    question_text = Paragraph(f"<b>Q{qa['id']}:</b> {clean_question}", question_style)
                    story.append(question_text)
                    
                    # Clean and format answer
                    clean_answer = PDFGenerator.clean_text(qa['answer'])
                    answer_text = Paragraph(f"<b>Answer:</b> {clean_answer}", answer_style)
                    story.append(answer_text)
                    
                    # Add spacer between Q&A pairs
                    if qa != qa_data['qa_pairs'][-1]:
                        story.append(Spacer(1, 0.1 * inch))
            
            # Add footer
            story.append(Spacer(1, 0.5 * inch))
            footer = Paragraph("Generated by Socratic", footer_style)
            story.append(footer)
            
            # Build PDF to buffer
            doc.build(story)
            buffer.seek(0)
            
            # Save directly to R2
            filename = f"reports/{output_filename}.pdf"  # Goes to 'media/reports/' in R2
            file_path = default_storage.save(filename, buffer)
            
            return file_path  # Returns path in R2
            
        except Exception as e:
            print(f"PDF generation failed: {str(e)}")
            return None
    
    @staticmethod
    def parse_markdown_text(text, normal_style=None, bullet_style=None, subheading_style=None):
        """
        Parse markdown text and convert to PDF elements
        """
        elements = []
        styles = getSampleStyleSheet()
        
        # Define styles for this method if not provided
        if normal_style is None:
            normal_style = ParagraphStyle(
                'NormalText',
                parent=styles['BodyText'],
                fontSize=10,
                leading=13,
                alignment=TA_JUSTIFY,
                spaceAfter=6
            )
        
        if subheading_style is None:
            subheading_style = ParagraphStyle(
                'SubHeadingStyle',
                parent=styles['Heading3'],
                fontSize=12,
                spaceBefore=12,
                spaceAfter=6,
                alignment=TA_LEFT,
                textColor='#1e7e34',  # Green
                fontName='Helvetica-Bold'
            )
        
        if bullet_style is None:
            bullet_style = ParagraphStyle(
                'BulletStyle',
                parent=styles['BodyText'],
                fontSize=10,
                leading=13,
                alignment=TA_JUSTIFY,
                leftIndent=20,
                spaceAfter=4
            )
        
        if not text:
            return [Paragraph("No summary available.", normal_style)]
        
        # Clean up any remaining markdown artifacts
        text = PDFGenerator.clean_markdown_artifacts(text)
        
        # Split into lines for processing
        lines = text.split('\n')
        i = 0
        
        while i < len(lines):
            line = lines[i].strip()
            
            if not line:
                i += 1
                continue
            
            # Handle headings (### or ##)
            heading_match = re.match(r'^(#{2,4})\s+(.+)', line)
            if heading_match:
                heading_text = heading_match.group(2).strip()
                # Remove any trailing # symbols
                heading_text = re.sub(r'#+$', '', heading_text).strip()
                elements.append(Paragraph(heading_text, subheading_style))
                i += 1
                continue
            
            # Handle bullet points (* or -)
            bullet_match = re.match(r'^[\*\-]\s+(.+)', line)
            if bullet_match:
                bullet_text = bullet_match.group(1).strip()
                formatted_text = PDFGenerator.format_markdown_to_html(bullet_text)
                elements.append(Paragraph(f"• {formatted_text}", bullet_style))
                i += 1
                continue
            
            # Handle numbered lists
            numbered_match = re.match(r'^(\d+)\.\s+(.+)', line)
            if numbered_match:
                number = numbered_match.group(1)
                list_text = numbered_match.group(2)
                formatted_text = PDFGenerator.format_markdown_to_html(list_text)
                elements.append(Paragraph(f"{number}. {formatted_text}", bullet_style))
                i += 1
                continue
            
            # Handle tables (look for pipe characters)
            if '|' in line and not line.startswith('|:') and '---' not in line:
                # Found a table row, collect the entire table
                table_data = []
                while i < len(lines) and '|' in lines[i]:
                    table_line = lines[i].strip()
                    if '---' not in table_line:  # Skip separator lines
                        # Split by pipe and clean up cells
                        cells = [cell.strip() for cell in table_line.split('|') if cell.strip()]
                        # Format each cell
                        formatted_cells = [Paragraph(PDFGenerator.format_markdown_to_html(cell), normal_style) for cell in cells]
                        table_data.append(formatted_cells)
                    i += 1
                
                if table_data and len(table_data) > 1:
                    # Create PDF table with GREEN styling
                    table = Table(table_data)
                    table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#28a745')),  # Green
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, 0), 10),
                        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8f9fa')),
                        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                        ('FONTSIZE', (0, 1), (-1, -1), 9),
                        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#dee2e6'))
                    ]))
                    elements.append(table)
                    elements.append(Spacer(1, 0.2 * inch))
                continue
            
            # Handle regular paragraphs with bold/italic
            if line:
                # Check if this is the start of a paragraph that continues
                paragraph_lines = [line]
                j = i + 1
                # Look ahead for continuation lines
                while j < len(lines):
                    next_line = lines[j].strip()
                    # Stop if we hit a blank line or special formatting
                    if not next_line or any(next_line.startswith(pattern) for pattern in ['###', '##', '* ', '- ', '|', '']):
                        break
                    # Also stop if next line looks like a numbered list or heading
                    if re.match(r'^(\d+\.|\#{2,4})\s', next_line):
                        break
                    paragraph_lines.append(next_line)
                    j += 1
                
                paragraph_text = ' '.join(paragraph_lines)
                formatted_paragraph = PDFGenerator.format_markdown_to_html(paragraph_text)
                elements.append(Paragraph(formatted_paragraph, normal_style))
                i = j
                continue
            
            i += 1
        
        return elements
    
    @staticmethod
    def clean_markdown_artifacts(text):
        """
        Remove or clean up markdown artifacts that shouldn't appear in final PDF
        """
        if not text:
            return ""
        
        # Remove standalone ### that aren't followed by text
        text = re.sub(r'^###\s*$', '', text, flags=re.MULTILINE)
        
        # Clean up multiple consecutive newlines
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Remove trailing # symbols from headings
        text = re.sub(r'(#{2,4}\s+.+?)\s*#+\s*$', r'\1', text, flags=re.MULTILINE)
        
        return text
    
    @staticmethod
    def format_markdown_to_html(text):
        """
        Convert markdown formatting to HTML tags for ReportLab
        """
        if not text:
            return ""
        
        # Handle **bold** text (must come before single asterisk)
        text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
        
        # Handle *italic* text
        text = re.sub(r'\*(.+?)\*', r'<i>\1</i>', text)
        
        # Handle __bold__ text
        text = re.sub(r'__(.+?)__', r'<b>\1</b>', text)
        
        # Handle _italic_ text
        text = re.sub(r'_(.+?)_', r'<i>\1</i>', text)
        
        return text
    
    @staticmethod
    def clean_text(text):
        """
        Clean and format text for better PDF rendering
        """
        if not text:
            return ""
        
        # Replace multiple spaces with single space
        text = ' '.join(text.split())
        
        # Handle special characters for XML/HTML
        text = text.replace('&', '&amp;')
        text = text.replace('<', '&lt;')
        text = text.replace('>', '&gt;')
        
        # Format markdown to HTML (this must come after escaping special chars)
        text = PDFGenerator.format_markdown_to_html(text)
        
        return text

class AdvancedPDFGenerator(PDFGenerator):
    """
    Extended PDF generator with advanced formatting options
    """
    
    @staticmethod
    def generate_report(processing_result, output_filename):
        """
        Generate a premium PDF with enhanced formatting - GREEN THEME
        """
        try:
            # Create PDF in memory
            buffer = BytesIO()
            
            # Create PDF document with premium layout
            doc = SimpleDocTemplate(
                buffer,
                pagesize=letter,
                rightMargin=36,
                leftMargin=36,
                topMargin=54,
                bottomMargin=54
            )
            
            styles = getSampleStyleSheet()
            
            # Premium styles - GREEN THEME
            premium_title_style = ParagraphStyle(
                'PremiumTitle',
                parent=styles['Heading1'],
                fontSize=18,
                spaceAfter=24,
                alignment=TA_CENTER,
                textColor='#155724',  # Dark green
                fontName='Helvetica-Bold'
            )
            
            premium_heading_style = ParagraphStyle(
                'PremiumHeading',
                parent=styles['Heading2'],
                fontSize=14,
                spaceBefore=24,
                spaceAfter=12,
                alignment=TA_LEFT,
                textColor='#28a745',  # Green
                borderColor='#28a745',
                borderWidth=1,
                borderPadding=5,
                backColor='#d4edda'  # Light green
            )
            
            premium_subheading_style = ParagraphStyle(
                'PremiumSubHeading',
                parent=styles['Heading3'],
                fontSize=12,
                spaceBefore=16,
                spaceAfter=8,
                alignment=TA_LEFT,
                textColor='#155724',  # Dark green
                fontName='Helvetica-Bold'
            )
            
            premium_normal_style = ParagraphStyle(
                'PremiumNormal',
                parent=styles['BodyText'],
                fontSize=10,
                leading=14,
                alignment=TA_JUSTIFY,
                spaceAfter=8
            )
            
            premium_bullet_style = ParagraphStyle(
                'PremiumBullet',
                parent=styles['BodyText'],
                fontSize=10,
                leading=14,
                alignment=TA_JUSTIFY,
                leftIndent=20,
                spaceAfter=6,
                textColor='#2c3e50'
            )
            
            premium_question_style = ParagraphStyle(
                'PremiumQuestion',
                parent=styles['BodyText'],
                fontSize=11,
                leading=15,
                spaceBefore=14,
                spaceAfter=8,
                fontName='Helvetica-Bold',
                textColor='#155724',  # Dark green
                leftIndent=0,
                backColor='#f8f9f9',
                borderColor='#c3e6cb',  # Light green border
                borderWidth=1,
                borderPadding=8
            )
            
            premium_answer_style = ParagraphStyle(
                'PremiumAnswer',
                parent=styles['BodyText'],
                fontSize=10,
                leading=14,
                leftIndent=10,
                spaceAfter=14,
                alignment=TA_JUSTIFY
            )
            
            # Footer style
            footer_style = ParagraphStyle(
                'FooterStyle',
                parent=styles['BodyText'],
                fontSize=10,
                alignment=TA_CENTER,
                textColor='#6c757d',
                fontName='Helvetica-Oblique',
                spaceBefore=30
            )
            
            story = []
            
            # Premium Title
            title = Paragraph(f"STUDY REPORT: {processing_result.document_title.upper()}", premium_title_style)
            story.append(title)
            story.append(Spacer(1, 0.3 * inch))
            
            # Context with better styling - GREEN THEME
            context_bg = '#d4edda' if processing_result.used_past_questions else '#fff3cd'  # Green or yellow
            context_border = '#c3e6cb' if processing_result.used_past_questions else '#ffeaa7'
            context_style = ParagraphStyle(
                'ContextStyle',
                parent=styles['BodyText'],
                fontSize=10,
                leading=13,
                alignment=TA_CENTER,
                backColor=context_bg,
                borderColor=context_border,
                borderWidth=1,
                borderPadding=10,
                spaceAfter=20
            )
            
            context_text = "Generated with past exam questions context" if processing_result.used_past_questions else "General study material"
            context = Paragraph(f"<b>Context:</b> {context_text}", context_style)
            story.append(context)
            story.append(Spacer(1, 0.4 * inch))
            
            # Summary section
            summary_title = Paragraph("Executive Summary", premium_heading_style)
            story.append(summary_title)
            
            # Process summary with enhanced markdown parsing
            summary_text = processing_result.summary
            formatted_summary = PDFGenerator.parse_markdown_text(
                summary_text, 
                premium_normal_style, 
                premium_bullet_style, 
                premium_subheading_style
            )
            
            for element in formatted_summary:
                story.append(element)
            
            story.append(Spacer(1, 0.4 * inch))
            
            # Q&A Section with enhanced styling
            qa_title = Paragraph("Knowledge Assessment", premium_heading_style)
            story.append(qa_title)
            story.append(Spacer(1, 0.2 * inch))
            
            qa_data = processing_result.questions_answers
            if 'qa_pairs' in qa_data:
                for i, qa in enumerate(qa_data['qa_pairs'], 1):
                    clean_question = PDFGenerator.clean_text(qa['question'])
                    clean_answer = PDFGenerator.clean_text(qa['answer'])
                    
                    # Question with enhanced styling
                    question_text = Paragraph(f"<b>Q{qa['id']}:</b> {clean_question}", premium_question_style)
                    story.append(question_text)
                    
                    # Answer
                    answer_text = Paragraph(f"<b>Answer:</b> {clean_answer}", premium_answer_style)
                    story.append(answer_text)
                    
                    # Page break logic for large Q&A sets
                    if i % 12 == 0 and i != len(qa_data['qa_pairs']):
                        story.append(PageBreak())
                        story.append(Paragraph("Knowledge Assessment (Continued)", premium_heading_style))
                        story.append(Spacer(1, 0.2 * inch))
                    else:
                        story.append(Spacer(1, 0.15 * inch))
            
            # Add footer
            story.append(Spacer(1, 0.5 * inch))
            footer = Paragraph("Generated by Socratic", footer_style)
            story.append(footer)
            
            # Build PDF to buffer
            doc.build(story)
            buffer.seek(0)
            
            # Save directly to R2
            filename = f"reports/{output_filename}.pdf"  # Goes to 'media/reports/' in R2
            file_path = default_storage.save(filename, buffer)
            
            return file_path  # Returns path in R2
            
        except Exception as e:
            print(f"Premium PDF generation failed: {str(e)}")
            # Fallback to basic generator
            return PDFGenerator.generate_report(processing_result, output_filename)
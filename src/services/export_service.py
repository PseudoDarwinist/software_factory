"""
Export Service - Multi-format document export for PRD Editor
Supports PDF, Word, Markdown, and HTML export with diagrams
"""

import io
import json
import logging
import base64
import tempfile
import subprocess
from datetime import datetime
from typing import Dict, List, Any, Optional, Union
from pathlib import Path

# PDF generation
try:
    from weasyprint import HTML, CSS
    from weasyprint.text.fonts import FontConfiguration
    WEASYPRINT_AVAILABLE = True
except ImportError:
    WEASYPRINT_AVAILABLE = False
    logging.warning("WeasyPrint not available - PDF export will be disabled")

# Word document generation
try:
    from docx import Document
    from docx.shared import Inches, Pt
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.enum.style import WD_STYLE_TYPE
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False
    Document = None  # Define fallback
    logging.warning("python-docx not available - Word export will be disabled")

# Markdown processing
try:
    import markdown
    from markdown.extensions import codehilite, tables, toc
    MARKDOWN_AVAILABLE = True
except ImportError:
    MARKDOWN_AVAILABLE = False
    logging.warning("markdown not available - enhanced Markdown export will be disabled")

# Image processing for diagrams
try:
    from PIL import Image
    import cairosvg
    IMAGE_PROCESSING_AVAILABLE = True
except ImportError:
    IMAGE_PROCESSING_AVAILABLE = False
    logging.warning("PIL/cairosvg not available - diagram export will be limited")

logger = logging.getLogger(__name__)

PANGOLIN_FONT_NAME = 'Pangolin'


class ExportService:
    """Service for exporting PRD documents in multiple formats"""
    
    def __init__(self):
        self.temp_dir = Path(tempfile.gettempdir()) / "prd_exports"
        self.temp_dir.mkdir(exist_ok=True)
        
    def export_document(self, content: Dict[str, Any], format_type: str, options: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Export document in specified format
        
        Args:
            content: Editor.js content structure
            format_type: 'pdf', 'docx', 'markdown', 'html'
            options: Export customization options
            
        Returns:
            Dict with export result and metadata
        """
        if not options:
            options = {}
            
        try:
            if format_type.lower() == 'pdf':
                if not WEASYPRINT_AVAILABLE:
                    return self._export_fallback_pdf(content, options)
                return self._export_pdf(content, options)
            elif format_type.lower() == 'docx':
                if not DOCX_AVAILABLE:
                    return self._export_fallback_docx(content, options)
                return self._export_docx(content, options)
            elif format_type.lower() == 'markdown':
                return self._export_markdown(content, options)
            elif format_type.lower() == 'html':
                return self._export_html(content, options)
            else:
                raise ValueError(f"Unsupported export format: {format_type}")
                
        except Exception as e:
            logger.error(f"Export failed for format {format_type}: {e}")
            raise
    
    def _export_pdf(self, content: Dict[str, Any], options: Dict[str, Any]) -> Dict[str, Any]:
        """Export to PDF with preserved formatting and embedded diagrams"""
        if not WEASYPRINT_AVAILABLE:
            raise RuntimeError("PDF export not available - WeasyPrint not installed")
            
        # Convert Editor.js content to HTML
        html_content = self._convert_to_html(content, options)
        
        # Create CSS for professional PDF styling
        css_content = self._get_pdf_css(options)
        
        # Generate PDF
        html_doc = HTML(string=html_content)
        css_doc = CSS(string=css_content)
        
        pdf_buffer = io.BytesIO()
        html_doc.write_pdf(pdf_buffer, stylesheets=[css_doc])
        pdf_buffer.seek(0)
        
        return {
            'success': True,
            'format': 'pdf',
            'content': pdf_buffer.getvalue(),
            'filename': f"prd_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
            'mime_type': 'application/pdf',
            'size': len(pdf_buffer.getvalue())
        }
    
    def _export_fallback_pdf(self, content: Dict[str, Any], options: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback PDF export using HTML conversion"""
        # Generate HTML and suggest user to print to PDF
        html_content = self._convert_to_html(content, options, standalone=True)
        html_bytes = html_content.encode('utf-8')
        
        return {
            'success': True,
            'format': 'html',  # Return as HTML for manual PDF conversion
            'content': html_bytes,
            'filename': f"prd_for_pdf_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html",
            'mime_type': 'text/html',
            'size': len(html_bytes),
            'note': 'PDF libraries not available. Use browser Print to PDF function.'
        }
    
    def _export_docx(self, content: Dict[str, Any], options: Dict[str, Any]) -> Dict[str, Any]:
        """Export to Word document with native table and diagram support"""
        if not DOCX_AVAILABLE or Document is None:
            raise RuntimeError("Word export not available - python-docx not installed")
            
        doc = Document()
        
        # Set document styles
        self._setup_docx_styles(doc, options)
        
        # Process Editor.js blocks
        blocks = content.get('blocks', [])
        
        for block in blocks:
            self._add_docx_block(doc, block, options)
        
        # Save to buffer
        docx_buffer = io.BytesIO()
        doc.save(docx_buffer)
        docx_buffer.seek(0)
        
        return {
            'success': True,
            'format': 'docx',
            'content': docx_buffer.getvalue(),
            'filename': f"prd_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx",
            'mime_type': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'size': len(docx_buffer.getvalue())
        }
    
    def _export_fallback_docx(self, content: Dict[str, Any], options: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback Word export using rich text format"""
        # Generate RTF content that can be opened by Word
        rtf_content = self._convert_to_rtf(content, options)
        rtf_bytes = rtf_content.encode('utf-8')
        
        return {
            'success': True,
            'format': 'rtf',
            'content': rtf_bytes,
            'filename': f"prd_{datetime.now().strftime('%Y%m%d_%H%M%S')}.rtf",
            'mime_type': 'application/rtf',
            'size': len(rtf_bytes),
            'note': 'Word libraries not available. Generated RTF format compatible with Word.'
        }
    
    def _export_markdown(self, content: Dict[str, Any], options: Dict[str, Any]) -> Dict[str, Any]:
        """Export to Markdown with proper syntax and diagram embedding"""
        markdown_content = self._convert_to_markdown(content, options)
        
        # Encode as UTF-8
        markdown_bytes = markdown_content.encode('utf-8')
        
        return {
            'success': True,
            'format': 'markdown',
            'content': markdown_bytes,
            'filename': f"prd_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
            'mime_type': 'text/markdown',
            'size': len(markdown_bytes)
        }
    
    def _export_html(self, content: Dict[str, Any], options: Dict[str, Any]) -> Dict[str, Any]:
        """Export to HTML with interactive features and styling"""
        html_content = self._convert_to_html(content, options, standalone=True)
        
        # Encode as UTF-8
        html_bytes = html_content.encode('utf-8')
        
        return {
            'success': True,
            'format': 'html',
            'content': html_bytes,
            'filename': f"prd_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html",
            'mime_type': 'text/html',
            'size': len(html_bytes)
        }
    
    def _convert_to_html(self, content: Dict[str, Any], options: Dict[str, Any], standalone: bool = False) -> str:
        """Convert Editor.js content to HTML"""
        blocks = content.get('blocks', [])
        html_parts = []
        
        if standalone:
            html_parts.append(self._get_html_header(options))
        
        for block in blocks:
            html_parts.append(self._convert_block_to_html(block, options))
        
        if standalone:
            html_parts.append(self._get_html_footer())
        
        return '\n'.join(html_parts)
    
    def _convert_to_markdown(self, content: Dict[str, Any], options: Dict[str, Any]) -> str:
        """Convert Editor.js content to Markdown"""
        blocks = content.get('blocks', [])
        markdown_parts = []
        
        # Add document header if specified
        if options.get('include_metadata', True):
            markdown_parts.append(f"# Product Requirements Document")
            markdown_parts.append(f"*Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
            markdown_parts.append("")
        
        for block in blocks:
            markdown_parts.append(self._convert_block_to_markdown(block, options))
        
        return '\n'.join(markdown_parts)
    
    def _convert_block_to_html(self, block: Dict[str, Any], options: Dict[str, Any]) -> str:
        """Convert a single Editor.js block to HTML"""
        block_type = block.get('type', 'paragraph')
        block_data = block.get('data', {})
        
        if block_type == 'header':
            level = block_data.get('level', 2)
            text = block_data.get('text', '')
            return f'<h{level}>{text}</h{level}>'
        
        elif block_type == 'paragraph':
            text = block_data.get('text', '')
            return f'<p>{text}</p>'
        
        elif block_type == 'list':
            items = block_data.get('items', [])
            style = block_data.get('style', 'unordered')
            tag = 'ul' if style == 'unordered' else 'ol'
            items_html = ''.join([f'<li>{item}</li>' for item in items])
            return f'<{tag}>{items_html}</{tag}>'
        
        elif block_type == 'table':
            return self._convert_table_to_html(block_data)
        
        elif block_type == 'quote':
            text = block_data.get('text', '')
            caption = block_data.get('caption', '')
            quote_html = f'<blockquote>{text}'
            if caption:
                quote_html += f'<cite>{caption}</cite>'
            quote_html += '</blockquote>'
            return quote_html
        
        elif block_type == 'mermaid':
            return self._convert_mermaid_to_html(block_data, options)
        
        elif block_type == 'section':
            title = block_data.get('title', '')
            html_content = block_data.get('html', '')
            return f'<div class="section"><h3>{title}</h3><div class="section-content">{html_content}</div></div>'
        
        else:
            # Fallback for unknown block types
            return f'<div class="unknown-block" data-type="{block_type}">{json.dumps(block_data)}</div>'
    
    def _convert_block_to_markdown(self, block: Dict[str, Any], options: Dict[str, Any]) -> str:
        """Convert a single Editor.js block to Markdown"""
        block_type = block.get('type', 'paragraph')
        block_data = block.get('data', {})
        
        if block_type == 'header':
            level = block_data.get('level', 2)
            text = block_data.get('text', '')
            return f"{'#' * level} {text}\n"
        
        elif block_type == 'paragraph':
            text = block_data.get('text', '')
            return f"{text}\n"
        
        elif block_type == 'list':
            items = block_data.get('items', [])
            style = block_data.get('style', 'unordered')
            marker = '-' if style == 'unordered' else '1.'
            items_md = '\n'.join([f"{marker} {item}" for item in items])
            return f"{items_md}\n"
        
        elif block_type == 'table':
            return self._convert_table_to_markdown(block_data)
        
        elif block_type == 'quote':
            text = block_data.get('text', '')
            caption = block_data.get('caption', '')
            quote_md = f"> {text}"
            if caption:
                quote_md += f"\n> \n> — {caption}"
            return f"{quote_md}\n"
        
        elif block_type == 'mermaid':
            code = block_data.get('code', '')
            return f"```mermaid\n{code}\n```\n"
        
        elif block_type == 'section':
            title = block_data.get('title', '')
            html_content = block_data.get('html', '')
            # Convert HTML content to markdown (basic conversion)
            content_md = self._html_to_markdown_basic(html_content)
            return f"## {title}\n\n{content_md}\n"
        
        else:
            return f"<!-- Unknown block type: {block_type} -->\n"
    
    def _convert_table_to_html(self, table_data: Dict[str, Any]) -> str:
        """Convert table data to HTML"""
        content = table_data.get('content', [])
        if not content:
            return '<table></table>'
        
        html = '<table class="prd-table">'
        
        # Add header row if present
        if content and len(content[0]) > 0:
            html += '<thead><tr>'
            for cell in content[0]:
                html += f'<th>{cell}</th>'
            html += '</tr></thead>'
        
        # Add body rows
        if len(content) > 1:
            html += '<tbody>'
            for row in content[1:]:
                html += '<tr>'
                for cell in row:
                    html += f'<td>{cell}</td>'
                html += '</tr>'
            html += '</tbody>'
        
        html += '</table>'
        return html
    
    def _convert_table_to_markdown(self, table_data: Dict[str, Any]) -> str:
        """Convert table data to Markdown"""
        content = table_data.get('content', [])
        if not content:
            return ''
        
        markdown = ''
        
        # Header row
        if content:
            header_row = '| ' + ' | '.join(content[0]) + ' |'
            separator_row = '| ' + ' | '.join(['---'] * len(content[0])) + ' |'
            markdown += f"{header_row}\n{separator_row}\n"
        
        # Data rows
        for row in content[1:]:
            data_row = '| ' + ' | '.join(row) + ' |'
            markdown += f"{data_row}\n"
        
        return f"{markdown}\n"
    
    def _convert_mermaid_to_html(self, mermaid_data: Dict[str, Any], options: Dict[str, Any]) -> str:
        """Convert Mermaid diagram to HTML with SVG embedding"""
        code = mermaid_data.get('code', '')
        
        # For HTML export, include the Mermaid code and let client-side rendering handle it
        return f'''
        <div class="mermaid-diagram">
            <pre class="mermaid">{code}</pre>
        </div>
        '''
    
    def _html_to_markdown_basic(self, html_content: str) -> str:
        """Basic HTML to Markdown conversion"""
        # This is a simplified conversion - in production, you might want to use a library like html2text
        import re
        
        # Remove HTML tags and convert basic formatting
        content = html_content
        content = re.sub(r'<p>(.*?)</p>', r'\1\n', content)
        content = re.sub(r'<strong>(.*?)</strong>', r'**\1**', content)
        content = re.sub(r'<em>(.*?)</em>', r'*\1*', content)
        content = re.sub(r'<li>(.*?)</li>', r'- \1', content)
        content = re.sub(r'<[^>]+>', '', content)  # Remove remaining HTML tags
        
        return content.strip()
    
    def _convert_to_rtf(self, content: Dict[str, Any], options: Dict[str, Any]) -> str:
        """Convert Editor.js content to RTF format"""
        blocks = content.get('blocks', [])
        rtf_parts = ['{\\rtf1\\ansi\\deff0 {\\fonttbl {\\f0 Times New Roman;}}']
        
        # Add document title if specified
        if options.get('include_metadata', True):
            title = options.get('title', 'Product Requirements Document')
            rtf_parts.append(f'\\f0\\fs28\\b {title}\\b0\\fs24\\par\\par')
        
        for block in blocks:
            rtf_parts.append(self._convert_block_to_rtf(block))
        
        rtf_parts.append('}')
        return ''.join(rtf_parts)
    
    def _convert_block_to_rtf(self, block: Dict[str, Any]) -> str:
        """Convert a single Editor.js block to RTF"""
        block_type = block.get('type', 'paragraph')
        block_data = block.get('data', {})
        
        if block_type == 'header':
            level = block_data.get('level', 2)
            text = block_data.get('text', '')
            font_size = max(16, 32 - level * 2)
            return f'\\fs{font_size}\\b {text}\\b0\\fs24\\par\\par'
        
        elif block_type == 'paragraph':
            text = block_data.get('text', '')
            # Remove HTML tags for RTF
            import re
            text = re.sub(r'<[^>]+>', '', text)
            return f'{text}\\par\\par'
        
        elif block_type == 'list':
            items = block_data.get('items', [])
            rtf_items = []
            for item in items:
                rtf_items.append(f'\\bullet {item}\\par')
            return ''.join(rtf_items) + '\\par'
        
        elif block_type == 'quote':
            text = block_data.get('text', '')
            caption = block_data.get('caption', '')
            quote_text = f'\\i {text}\\i0'
            if caption:
                quote_text += f'\\par\\fs20 — {caption}\\fs24'
            return f'{quote_text}\\par\\par'
        
        else:
            return f'[{block_type} block]\\par\\par'
    
    def _get_html_header(self, options: Dict[str, Any]) -> str:
        """Get HTML document header with styling"""
        title = options.get('title', 'Product Requirements Document')
        
        return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    {self._get_mermaid_script_tag()}
    <style>
        {self._get_html_css(options)}
    </style>
</head>
<body>
    <div class="document-container">
        <header class="document-header">
            <h1>{title}</h1>
            <p class="generated-date">Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </header>
        <main class="document-content">'''
    
    def _get_html_footer(self) -> str:
        """Get HTML document footer"""
        return '''        </main>
    </div>
    <script>
        mermaid.initialize({ startOnLoad: true, theme: 'default' });
    </script>
</body>
</html>'''
    
    def _get_pangolin_font_css(self) -> str:
        """Embed Pangolin font as a data URI if available, else empty string"""
        try:
            project_root = Path(__file__).resolve().parents[2]
            font_path = project_root / 'frontend' / 'fonts' / 'Pangolin-Regular.ttf'
            if font_path.exists():
                import base64
                b64 = base64.b64encode(font_path.read_bytes()).decode('ascii')
                return f"""
        @font-face {{
            font-family: '{PANGOLIN_FONT_NAME}';
            src: url(data:font/ttf;base64,{b64}) format('truetype');
            font-weight: normal;
            font-style: normal;
            font-display: swap;
        }}
                """
            else:
                logger.warning(f"Pangolin font not found at {font_path}")
                return ''
        except Exception as e:
            logger.warning(f"Failed to embed Pangolin font: {e}")
            return ''

    def _get_mermaid_script_tag(self) -> str:
        """Return a <script> tag with local Mermaid embedded if available; otherwise CDN."""
        try:
            project_root = Path(__file__).resolve().parents[2]
            mermaid_path = project_root / 'frontend' / 'vendor' / 'mermaid' / 'mermaid.min.js'
            if mermaid_path.exists():
                js = mermaid_path.read_text(encoding='utf-8', errors='ignore')
                return f'<script>{js}</script>'
        except Exception as e:
            logger.warning(f"Failed to embed Mermaid locally: {e}")
        # Fallback to CDN
        return '<script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>'

    def _get_html_css(self, options: Dict[str, Any]) -> str:
        """Get CSS for HTML export"""
        font_face_css = self._get_pangolin_font_css()
        return f"{font_face_css}\n" + """
        body {
            font-family: 'Pangolin', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #fff;
        }
        
        .document-header {
            border-bottom: 2px solid #e1e8ed;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }
        
        .document-header h1 {
            margin: 0;
            color: #1a202c;
            font-size: 2.5rem;
        }
        
        .generated-date {
            color: #64748b;
            font-style: italic;
            margin: 10px 0 0 0;
        }
        
        h1, h2, h3, h4, h5, h6 {
            color: #1a202c;
            margin-top: 2rem;
            margin-bottom: 1rem;
        }
        
        h2 {
            border-bottom: 1px solid #e1e8ed;
            padding-bottom: 0.5rem;
        }
        
        .prd-table {
            width: 100%;
            border-collapse: collapse;
            margin: 1rem 0;
        }
        
        .prd-table th,
        .prd-table td {
            border: 1px solid #e1e8ed;
            padding: 12px;
            text-align: left;
        }
        
        .prd-table th {
            background-color: #f8fafc;
            font-weight: 600;
        }
        
        blockquote {
            border-left: 4px solid #3b82f6;
            margin: 1rem 0;
            padding: 1rem;
            background-color: #f8fafc;
        }
        
        .mermaid-diagram {
            margin: 2rem 0;
            text-align: center;
        }
        
        .section {
            margin: 2rem 0;
            padding: 1rem;
            border: 1px solid #e1e8ed;
            border-radius: 8px;
        }
        
        .section h3 {
            margin-top: 0;
            color: #3b82f6;
        }
        
        @media print {
            body { font-size: 12pt; }
            .document-header { page-break-after: avoid; }
            h1, h2, h3 { page-break-after: avoid; }
        }
        """
    
    def _get_pdf_css(self, options: Dict[str, Any]) -> str:
        """Get CSS specifically for PDF generation"""
        font_face_css = self._get_pangolin_font_css()
        return f"{font_face_css}\n" + """
        @page {
            size: A4;
            margin: 2cm;
        }
        
        body {
            font-family: 'Pangolin', 'DejaVu Sans', Arial, sans-serif;
            font-size: 11pt;
            line-height: 1.4;
            color: #333;
        }
        
        h1 { font-size: 24pt; margin-bottom: 12pt; }
        h2 { font-size: 18pt; margin-top: 18pt; margin-bottom: 8pt; border-bottom: 1pt solid #ccc; }
        h3 { font-size: 14pt; margin-top: 14pt; margin-bottom: 6pt; }
        h4 { font-size: 12pt; margin-top: 12pt; margin-bottom: 4pt; }
        
        p { margin-bottom: 8pt; }
        
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 12pt 0;
        }
        
        th, td {
            border: 1pt solid #ccc;
            padding: 6pt;
            text-align: left;
        }
        
        th {
            background-color: #f5f5f5;
            font-weight: bold;
        }
        
        blockquote {
            border-left: 3pt solid #3b82f6;
            margin: 12pt 0;
            padding: 8pt;
            background-color: #f8f9fa;
        }
        
        .mermaid-diagram {
            page-break-inside: avoid;
            margin: 12pt 0;
        }
        """
    
    def _setup_docx_styles(self, doc: Any, options: Dict[str, Any]):
        """Setup Word document styles"""
        styles = doc.styles
        
        # Set default document font if available
        try:
            normal_style = styles['Normal']
            normal_style.font.name = PANGOLIN_FONT_NAME
        except Exception:
            pass
        
        # Create custom styles if they don't exist
        try:
            # Heading styles
            for i in range(1, 7):
                style_name = f'Heading {i}'
                if style_name not in styles:
                    heading_style = styles.add_style(style_name, WD_STYLE_TYPE.PARAGRAPH)
                    heading_style.font.bold = True
                    heading_style.font.size = Pt(18 - i * 2)
        except:
            pass  # Styles might already exist
    
    def _add_docx_block(self, doc: Any, block: Dict[str, Any], options: Dict[str, Any]):
        """Add a single Editor.js block to Word document"""
        block_type = block.get('type', 'paragraph')
        block_data = block.get('data', {})
        
        if block_type == 'header':
            level = block_data.get('level', 2)
            text = block_data.get('text', '')
            heading = doc.add_heading(text, level=level)
        
        elif block_type == 'paragraph':
            text = block_data.get('text', '')
            doc.add_paragraph(text)
        
        elif block_type == 'list':
            items = block_data.get('items', [])
            for item in items:
                doc.add_paragraph(item, style='List Bullet')
        
        elif block_type == 'table':
            self._add_docx_table(doc, block_data)
        
        elif block_type == 'quote':
            text = block_data.get('text', '')
            caption = block_data.get('caption', '')
            quote_text = text
            if caption:
                quote_text += f" — {caption}"
            quote_para = doc.add_paragraph(quote_text)
            quote_para.style = 'Quote'
        
        elif block_type == 'mermaid':
            # Add placeholder for Mermaid diagram
            code = block_data.get('code', '')
            doc.add_paragraph(f"[Mermaid Diagram]\n{code}", style='Code')
        
        elif block_type == 'section':
            title = block_data.get('title', '')
            html_content = block_data.get('html', '')
            doc.add_heading(title, level=3)
            # Convert HTML content to plain text for Word
            plain_content = self._html_to_markdown_basic(html_content)
            doc.add_paragraph(plain_content)
    
    def _add_docx_table(self, doc: Any, table_data: Dict[str, Any]):
        """Add table to Word document"""
        content = table_data.get('content', [])
        if not content:
            return
        
        rows = len(content)
        cols = len(content[0]) if content else 0
        
        if rows == 0 or cols == 0:
            return
        
        table = doc.add_table(rows=rows, cols=cols)
        table.style = 'Table Grid'
        
        for i, row_data in enumerate(content):
            row = table.rows[i]
            for j, cell_data in enumerate(row_data):
                if j < len(row.cells):
                    row.cells[j].text = str(cell_data)


# Global export service instance
_export_service = None

def get_export_service() -> ExportService:
    """Get the global export service instance"""
    global _export_service
    if _export_service is None:
        _export_service = ExportService()
    return _export_service
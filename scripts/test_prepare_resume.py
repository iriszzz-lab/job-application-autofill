import tempfile
import importlib.util
from pathlib import Path
import unittest
from zipfile import ZipFile
from xml.sax.saxutils import escape

from prepare_resume import extract_resume


class ResumeExtractionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_utf8_resume_preserves_objective_facts_and_omits_credentials(self):
        path = self.root / 'resume.txt'
        path.write_text('Synthetic Candidate\nEducation: Synthetic University\n2024-09 — Present\n\nPassword: SYNTHETIC_SECRET', encoding='utf-8')
        result = extract_resume(path)
        text = '\n'.join(b['text'] for b in result['blocks'])
        self.assertIn('2024-09 — Present', text)
        self.assertIn('Synthetic University', text)
        self.assertNotIn('SYNTHETIC_SECRET', text)
        self.assertEqual(result['status'], 'ready_for_fact_review')

    def test_docx_preserves_tables_headers_and_textboxes(self):
        path = self.root / 'resume.docx'
        ns='http://schemas.openxmlformats.org/wordprocessingml/2006/main'
        def p(text):
            return '<w:p><w:r><w:t>'+escape(text)+'</w:t></w:r></w:p>'
        xml=f'<w:document xmlns:w="{ns}"><w:body>'+p('Education')+'<w:tbl><w:tr><w:tc>'+p('Synthetic University')+'</w:tc><w:tc>'+p('2020-09 — 2024-06')+'</w:tc></w:tr></w:tbl><w:p><w:r><w:txbxContent>'+p('Project in text box')+'</w:txbxContent></w:r></w:p></w:body></w:document>'
        with ZipFile(path, 'w') as archive:
            archive.writestr('word/document.xml', xml)
            archive.writestr('word/header1.xml', f'<w:hdr xmlns:w="{ns}">'+p('Synthetic Candidate')+'</w:hdr>')
        result = extract_resume(path)
        text = '\n'.join(b['text'] for b in result['blocks'])
        for value in ['Synthetic University', '2020-09 — 2024-06', 'Project in text box', 'Synthetic Candidate']:
            self.assertEqual(text.count(value), 1)
        self.assertIn('table_cell_order_requires_visual_review', result['warnings'])
        self.assertEqual(len({b['source_id'] for b in result['blocks']}), len(result['blocks']))

    def test_image_does_not_claim_fake_ocr(self):
        path = self.root / 'resume.png'
        path.write_bytes(b'synthetic-image-fixture')
        result = extract_resume(path)
        self.assertEqual(result['status'], 'needs_vision_or_ocr')
        self.assertEqual(result['blocks'], [])

    @unittest.skipUnless(importlib.util.find_spec('pypdf'), 'Install the resume extra for PDF tests')
    def test_blank_pdf_requires_vision_instead_of_empty_profile(self):
        from pypdf import PdfWriter
        path = self.root / 'resume.pdf'
        writer = PdfWriter()
        writer.add_blank_page(width=612, height=792)
        writer.write(path)
        result = extract_resume(path)
        self.assertEqual(result['status'], 'needs_vision_or_ocr')
        self.assertIn('page:1:vision_or_ocr_required', result['warnings'])

    def test_unsupported_doc_has_actionable_failure(self):
        with self.assertRaisesRegex(ValueError, 'unsupported_resume_format'):
            extract_resume(self.root / 'resume.doc')

    @unittest.skipUnless(importlib.util.find_spec('pypdf'), 'Install the resume extra for PDF tests')
    def test_text_pdf_retains_all_pages_and_source_locations(self):
        from pypdf import PdfWriter
        from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject
        path = self.root / 'text-resume.pdf'
        writer = PdfWriter()
        for text in ['Synthetic University Education Computer Science 2020 2024',
                     'Synthetic Employer Internship Engineer Project Objective facts']:
            page = writer.add_blank_page(width=612, height=792)
            font = DictionaryObject({NameObject('/Type'): NameObject('/Font'),
                                     NameObject('/Subtype'): NameObject('/Type1'),
                                     NameObject('/BaseFont'): NameObject('/Helvetica')})
            page[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'): DictionaryObject({NameObject('/F1'): font})})
            stream = DecodedStreamObject()
            stream.set_data(('BT /F1 12 Tf 40 700 Td (' + text + ') Tj ET').encode())
            page[NameObject('/Contents')] = writer._add_object(stream)
        writer.write(path)
        result = extract_resume(path)
        self.assertEqual(result['status'], 'ready_for_fact_review')
        self.assertEqual([b['location'] for b in result['blocks']], ['page:1', 'page:2'])
        self.assertIn('Synthetic University', result['blocks'][0]['text'])
        self.assertIn('Synthetic Employer', result['blocks'][1]['text'])

    def test_multiline_credential_is_removed_without_dropping_token_project_prose(self):
        path = self.root / 'resume.md'
        path.write_text('Password:\n\nSYNTHETIC_SECRET\n\nProject: token embeddings for synthetic search', encoding='utf-8')
        result = extract_resume(path)
        text = '\n'.join(b['text'] for b in result['blocks'])
        self.assertNotIn('SYNTHETIC_SECRET', text)
        self.assertIn('token embeddings', text)

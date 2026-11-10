"""Extract source blocks from a resume; never infer candidate facts or submit forms."""
import argparse
import json
from pathlib import Path
import re
import sys
from zipfile import ZipFile, BadZipFile
from xml.etree import ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from edge_form_graph.contracts import SENSITIVE

W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'


def safe_text(text, pending=None):
    # Keep resume prose (e.g. token embeddings); remove credential assignments.
    pending = pending if pending is not None else [False]
    lines = []
    for line in text.splitlines():
        prefix = re.split(r'[:=：]', line, maxsplit=1)[0].strip()
        credential_label = SENSITIVE.search(prefix)
        if pending[0] and line.strip():
            lines.append('[credential value omitted]')
            pending[0] = False
        elif credential_label and (re.search(r'[:=：]', line) or SENSITIVE.fullmatch(line.strip())):
            lines.append('[credential line omitted]')
            pending[0] = bool(SENSITIVE.fullmatch(line.strip()) or re.search(r'[:=：]\s*$', line))
        else:
            lines.append(line)
    return '\n'.join(lines).strip()


def extract_resume(path):
    path = Path(path).expanduser().resolve()
    suffix = path.suffix.lower()
    blocks, warnings = [], []
    pending_credential = [False]
    def add(location, text):
        text = safe_text(text, pending_credential)
        if text:
            blocks.append({'source_id': f'block-{len(blocks)+1:04d}', 'location': location, 'text': text})
    if suffix in {'.txt', '.md'}:
        data = path.read_bytes()
        try:
            text = data.decode('utf-8-sig')
        except UnicodeDecodeError:
            text = data.decode('gb18030')
            warnings.append('legacy_text_encoding_check_required')
        for index, paragraph in enumerate(re.split(r'\n\s*\n', text), 1):
            add(f'paragraph:{index}', paragraph)
    elif suffix == '.docx':
        def paragraph_text(node):
            if node.tag == W+'t':
                return node.text or ''
            if node.tag in {W+'tab', W+'br'}:
                return '\n' if node.tag == W+'br' else '\t'
            return ''.join(paragraph_text(child) for child in node if child.tag != W+'p')
        with ZipFile(path) as archive:
            parts = ['word/document.xml'] + sorted(n for n in archive.namelist()
                     if re.fullmatch(r'word/(header|footer)\d+\.xml', n))
            for part in parts:
                root = ET.fromstring(archive.read(part))
                for index, paragraph in enumerate(root.iter(W+'p'), 1):
                    add(f'{part}:paragraph:{index}', paragraph_text(paragraph))
                if any(True for _ in root.iter(W+'tbl')):
                    warnings.append('table_cell_order_requires_visual_review')
                if any(True for _ in root.iter(W+'drawing')):
                    warnings.append('embedded_images_require_visual_review')
        warnings.append('docx_layout_requires_review')
    elif suffix == '.pdf':
        try:
            from pypdf import PdfReader
        except ImportError as error:
            raise ValueError('pdf_dependency_missing: pip install -e ".[resume]"') from error
        try:
            reader = PdfReader(path)
        except Exception as error:
            raise ValueError('pdf_unreadable: provide_a_readable_or_unlocked_copy') from error
        if reader.is_encrypted:
            raise ValueError('encrypted_pdf: provide_an_unlocked_copy')
        for index, page in enumerate(reader.pages, 1):
            text = page.extract_text() or ''
            add(f'page:{index}', text)
            if len(re.sub(r'\s', '', text)) < 40:
                warnings.append(f'page:{index}:vision_or_ocr_required')
        warnings.append('pdf_reading_order_requires_visual_review')
    elif suffix in {'.png', '.jpg', '.jpeg', '.webp', '.tif', '.tiff'}:
        if not path.is_file():
            raise ValueError('resume_file_missing')
        warnings.append('image_requires_host_vision_or_local_ocr')
    else:
        raise ValueError('unsupported_resume_format: provide_PDF_DOCX_text_or_image')
    vision = not blocks or any('ocr_required' in warning for warning in warnings)
    return {'schema': 'resume-source-v1', 'source_file': str(path),
            'status': 'needs_vision_or_ocr' if vision else 'ready_for_fact_review',
            'blocks': blocks, 'warnings': list(dict.fromkeys(warnings)),
            'notice': 'Source text only. Layout, facts and conflicts require review before profile creation.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        output = args.output.expanduser().resolve()
        project = Path(__file__).resolve().parents[1]
        if output.is_relative_to(project):
            raise ValueError('resume_output_must_stay_outside_repository')
        if output.exists():
            raise ValueError('existing_extraction_not_overwritten')
        result = extract_resume(args.input)
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open('x', encoding='utf-8') as stream:
            json.dump(result, stream, ensure_ascii=False, indent=2)
        print(json.dumps({'status': result['status'], 'blocks': len(result['blocks']),
                          'warnings': result['warnings']}, ensure_ascii=False))
        return 0
    except (OSError, ValueError, ET.ParseError, BadZipFile) as error:
        print(json.dumps({'status': 'blocked', 'error': str(error)}, ensure_ascii=False))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())

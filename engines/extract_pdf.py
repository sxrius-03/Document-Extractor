"""
extract_pdf.py — Extrator de PDFs para Markdown estruturado
Usa Docling (IBM) para preservar hierarquia, tabelas e layout acadêmico.
Saída: arquivos .md prontos para uso como base de conhecimento do TPA.

Fases de configuração:
  Fase 1 (concluída): conversão base, tabelas estruturadas
  Fase 2 (concluída): extração de imagens via Docling (generate_picture_images)
  Fase 3 (atual): OCR com Tesseract PT para PDFs com encoding quebrado
"""

import os
import re
import sys

from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.datamodel.base_models import InputFormat

# Forçar UTF-8 no console do Windows
sys.stdout.reconfigure(encoding='utf-8', errors='replace')


# ──────────────────────────────────────────────
# CONFIGURAÇÃO
# ──────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOCS_DIR = os.path.join(BASE_DIR, "pdfs")
OUT_DIR  = os.path.join(BASE_DIR, "md_out")
IMG_DIR  = os.path.join(OUT_DIR, "_imagens")

# Fase 3: Tesseract PT via pytesseract
TESSERACT_CMD      = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
TESSDATA_PREFIX    = os.path.join(os.path.expanduser("~"), ".tessdata")
OCR_BROKEN_THRESH  = 0.05   # ratio mínimo de chars quebrados para acionar OCR
OCR_LANG           = "por"

# Configurar pytesseract se disponível
_pytesseract_ok = False
try:
    import pytesseract
    from PIL import Image as PILImage
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD
    os.environ.setdefault("TESSDATA_PREFIX", TESSDATA_PREFIX)
    _pytesseract_ok = os.path.isfile(TESSERACT_CMD)
except ImportError:
    pass

# EasyOCR — carregado sob demanda (modelos ~100MB, só baixa uma vez)
_easyocr_reader = None

def _get_easyocr_reader():
    global _easyocr_reader
    if _easyocr_reader is not None:
        return _easyocr_reader
    try:
        import easyocr as _easyocr_mod
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            _easyocr_reader = _easyocr_mod.Reader(["en"], gpu=False, verbose=False)
        return _easyocr_reader
    except Exception:
        return None


# ──────────────────────────────────────────────
# TABELAS DE CONVERSÃO SUB/SUPERSCRIPT UNICODE
# ──────────────────────────────────────────────
_SUB_SAFE = {
    '0':'₀','1':'₁','2':'₂','3':'₃','4':'₄',
    '5':'₅','6':'₆','7':'₇','8':'₈','9':'₉',
    '+':'₊','-':'₋',
}
_SUP_SAFE = {
    '0':'⁰','1':'¹','2':'²','3':'³','4':'⁴',
    '5':'⁵','6':'⁶','7':'⁷','8':'⁸','9':'⁹',
    '+':'⁺','-':'⁻','n':'ⁿ','x':'ˣ','a':'ᵃ',
}


def _apply_sub(text: str) -> str:
    return ''.join(_SUB_SAFE.get(c, c) for c in text)

def _apply_sup(text: str) -> str:
    return ''.join(_SUP_SAFE.get(c, c) for c in text)


def build_converter() -> DocumentConverter:
    """Cria e configura o DocumentConverter do Docling."""
    opts = PdfPipelineOptions()
    opts.do_table_structure = True       # tabelas como Markdown tables
    opts.do_ocr = False                  # OCR feito via pytesseract (Fase 3)
    opts.generate_picture_images = True  # captura recortes de imagem por figura
    opts.images_scale = 2.0              # 144 dpi efetivo
    return DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=opts)}
    )


# Instanciar uma vez — carrega modelos de layout na inicialização
CONVERTER = build_converter()

def set_num_threads(threads: int):
    """Atualiza o número de threads do conversor em tempo de execução."""
    os.environ["OMP_NUM_THREADS"] = str(threads)
    os.environ["MKL_NUM_THREADS"] = str(threads)
    try:
        from docling.datamodel.pipeline_options import AcceleratorOptions
        CONVERTER.format_options[InputFormat.PDF].pipeline_options.accelerator_options = AcceleratorOptions(num_threads=threads)
    except Exception:
        pass



# ──────────────────────────────────────────────
# FUNÇÕES AUXILIARES
# ──────────────────────────────────────────────

def sanitize_filename(name: str) -> str:
    """Remove caracteres problemáticos do nome de arquivo, mantendo legibilidade."""
    name = re.sub(r'\.pdf$', '', name, flags=re.IGNORECASE)
    name = re.sub(r'[<>:"/\\|?*]', '_', name)
    name = re.sub(r'_+', '_', name)
    if len(name) > 120:
        name = name[:120]
    return name.strip('_ ')


def build_header(filename: str, meta: dict, category: str) -> str:
    """Gera o cabeçalho padronizado (Reference Card) para o Markdown."""
    titulo = meta['titulo'] or filename
    autor  = meta['autor'] or '*(não detectado nos metadados)*'

    header = f"""# {titulo}

## 📑 Ficha de Referência
| Campo | Valor |
|-------|-------|
| **Arquivo** | `{filename}` |
| **Autor(es)** | {autor} |
| **Categoria** | {category} |
| **Páginas** | {meta['paginas']} |

---

## 📄 Conteúdo Extraído

"""
    return header


def detect_category(filepath: str) -> str:
    """Detecta a categoria temática com base no caminho do arquivo."""
    path_lower = filepath.lower()
    if 'carne' in path_lower:
        return 'Tecnologia de Carnes'
    elif 'leite' in path_lower or 'queijo' in path_lower:
        return 'Tecnologia de Leite / Laticínios'
    elif 'micro' in path_lower or 'microbiologia' in path_lower:
        return 'Microbiologia de Alimentos'
    else:
        return 'Geral'


def clean_markdown(md_text: str) -> str:
    """Limpeza pós-extração do Markdown gerado."""
    md_text = re.sub(r'^\s*\d{1,3}\s*$', '', md_text, flags=re.MULTILINE)
    md_text = re.sub(r'\n{4,}', '\n\n\n', md_text)
    md_text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', md_text)
    return md_text.strip()


_MIME_TO_EXT = {"image/png": "png", "image/jpeg": "jpg", "image/tiff": "tif"}
_MIN_PX_SAVE = 80   # tamanho mínimo para salvar como arquivo em _imagens/
_MIN_PX_OCR  = 8    # tamanho mínimo para tentar OCR (fórmulas e íons inline são pequenos)
_MIN_OCR_CHARS = 2  # mínimo de chars para aceitar resultado OCR (fórmulas podem ser curtas)
_OCR_UPSCALE_TARGET = 80  # escalar imagens pequenas para pelo menos esse tamanho antes do OCR


def _ocr_image(pil_img, inline: bool = False) -> str:
    """
    OCR em imagem PIL.
    inline=True  → EasyOCR (melhor para fórmulas/íons); fallback Tesseract PSM 7.
    inline=False → Tesseract PSM 6 (bloco uniforme para figuras grandes).
    """
    if inline:
        return _ocr_inline_easyocr(pil_img) or _ocr_inline_tesseract(pil_img)
    return _ocr_block_tesseract(pil_img)


def _upscale(pil_img, scale: int = 8):
    return pil_img.resize((pil_img.width * scale, pil_img.height * scale), PILImage.LANCZOS)


def _ocr_inline_easyocr(pil_img) -> str:
    """
    EasyOCR com detecção de posição vertical para sub/superscripts.
    Cada segmento detectado é classificado por y_center relativo à baseline:
      - abaixo da baseline (y_center > baseline + margem) → subscript Unicode
      - acima da baseline (y_center < baseline - margem)  → superscript Unicode
      - zona central                                       → texto normal
    """
    reader = _get_easyocr_reader()
    if reader is None:
        return ""
    try:
        import numpy as np
        import warnings

        big = _upscale(pil_img, 8)
        img_h = big.height
        arr = np.array(big)

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            results = reader.readtext(arr, detail=1, paragraph=False)

        if not results:
            return ""

        segments = []
        for bbox, text, conf in results:
            text = text.strip()
            if not text:
                continue
            ys = [p[1] for p in bbox]
            xs = [p[0] for p in bbox]
            y_top = min(ys)
            y_bot = max(ys)
            seg_h = y_bot - y_top
            segments.append({
                "text":    text,
                "x":       min(xs),
                "y_top":   y_top,
                "y_bot":   y_bot,
                "y_mid":   (y_top + y_bot) / 2,
                "height":  seg_h,
            })

        if not segments:
            return ""

        # Classificação por posição absoluta relativa à altura da imagem:
        #   subscript  → y_top  > img_h * 0.45  (começa na metade inferior)
        #   superscript → y_bot < img_h * 0.55  (termina na metade superior)
        #   ambos exigem segmento pequeno (< 55% da altura total = não é texto principal)
        sub_thresh  = img_h * 0.45  # subscripts começam abaixo deste y
        sup_thresh  = img_h * 0.55  # superscripts terminam acima deste y
        small_limit = img_h * 0.55  # segmentos grandes = texto principal

        # Ordenar da esquerda para a direita
        segments.sort(key=lambda s: s["x"])

        parts = []
        for seg in segments:
            text     = seg["text"]
            is_small = seg["height"] < small_limit

            if is_small and seg["y_top"] > sub_thresh:   # abaixo → subscript
                parts.append(_apply_sub(text))
            elif is_small and seg["y_bot"] < sup_thresh:  # acima  → superscript
                parts.append(_apply_sup(text))
            else:                                          # texto principal
                parts.append(text)

        result = "".join(parts)
        return result if len(result) >= _MIN_OCR_CHARS else ""
    except Exception:
        return ""


def _ocr_inline_tesseract(pil_img) -> str:
    if not _pytesseract_ok:
        return ""
    try:
        w, h = pil_img.size
        short = min(w, h)
        scale = max(1, _OCR_UPSCALE_TARGET // short + 1) if short > 0 else 1
        big = pil_img.resize((w * scale, h * scale), PILImage.LANCZOS)
        text = pytesseract.image_to_string(big, lang=OCR_LANG, config="--psm 7").strip()
        return text if len(text) >= _MIN_OCR_CHARS else ""
    except Exception:
        return ""


def _ocr_block_tesseract(pil_img) -> str:
    if not _pytesseract_ok:
        return ""
    try:
        text = pytesseract.image_to_string(pil_img, lang=OCR_LANG, config="--psm 6").strip()
        return text if len(text) >= _MIN_OCR_CHARS else ""
    except Exception:
        return ""


def extract_images_with_ocr(doc, img_subdir: str, safe_name: str) -> tuple:
    """
    Processa TODAS as pictures do documento (inclusive fórmulas inline pequenas)
    para manter alinhamento com os marcadores <!-- image --> do markdown Docling.

    Retorna (figure_count, [(img_rel_path|None, page, ocr_text, is_figure), ...]).
    - is_figure=True  → imagem grande, salva em _imagens/ e referenciada no md
    - is_figure=False → fórmula/símbolo inline, só texto OCR inserido no md
    """
    os.makedirs(img_subdir, exist_ok=True)
    figure_count = 0
    results = []

    for i, pic in enumerate(doc.pictures):
        img_ref = pic.image
        page = pic.prov[0].page_no if pic.prov else 0

        if not img_ref or not img_ref.pil_image:
            # Docling marcou mas não gerou imagem — mantém placeholder para alinhamento
            results.append((None, page, "", False))
            continue

        w, h = img_ref.pil_image.size
        ext = _MIME_TO_EXT.get(img_ref.mimetype, "png")
        is_figure = w >= _MIN_PX_SAVE and h >= _MIN_PX_SAVE

        if is_figure:
            img_filename = f"p{page}_fig{i+1}.{ext}"
            img_ref.pil_image.save(os.path.join(img_subdir, img_filename))
            figure_count += 1
            img_rel = f"_imagens/{safe_name}/{img_filename}"
        else:
            img_rel = None  # inline — não salva arquivo

        if w >= _MIN_PX_OCR and h >= _MIN_PX_OCR:
            ocr_text = _ocr_image(img_ref.pil_image, inline=not is_figure)
        else:
            ocr_text = ""

        results.append((img_rel, page, ocr_text, is_figure))

    return figure_count, results


def inject_ocr_into_markdown(md_text: str, ocr_results: list) -> str:
    """
    Substitui marcadores <!-- image --> do Docling em ordem do documento:
    - Figura grande: referência de imagem + blockquote com OCR (se houver texto)
    - Inline (fórmula/íon): texto OCR em backtick diretamente no fluxo
    """
    it = iter(ocr_results)

    def _replace(match):
        try:
            img_rel, page, ocr_text, is_figure = next(it)
        except StopIteration:
            return match.group(0)

        if is_figure:
            img_md = f"![Figura pág.{page}]({img_rel})"
            if ocr_text:
                indented = ocr_text.replace("\n", "\n> ")
                return f"{img_md}\n\n> **Texto na imagem:**\n> {indented}"
            return img_md
        else:
            # Fórmula/símbolo inline: insere texto no fluxo
            return f"`{ocr_text}`" if ocr_text else ""

    return re.sub(r'<!-- image -->', _replace, md_text)


def _inject_inline_fitz_ocr(md_text: str, pdf_path: str) -> tuple:
    """
    Usa PyMuPDF para encontrar imagens inline que o Docling não classificou como
    PictureItem (fórmulas químicas, íons, símbolos matemáticos).
    Lê o canal smask (máscara de opacidade) onde o glifo realmente está,
    faz OCR e injeta o texto no markdown usando o contexto de palavras adjacentes.
    Retorna (md_text_modificado, contagem_injetada).
    """
    if not _pytesseract_ok:
        return md_text, 0

    import fitz
    import io

    try:
        doc = fitz.open(pdf_path)
    except Exception:
        return md_text, 0

    # (anchor_text, ocr_text) em ordem de documento
    injections = []

    for page_num in range(doc.page_count):
        page = doc[page_num]
        img_infos = page.get_image_info(xrefs=True)
        if not img_infos:
            continue

        # smask por xref (usa primeiro encontrado; mesmo xref → mesma máscara)
        xref_to_smask = {img[0]: img[1] for img in page.get_images(full=True)}
        words = page.get_text("words")  # (x0,y0,x1,y1,word, ...)

        page_items = []
        ocr_cache = {}  # xref → ocr_text (evita re-OCR de duplicatas)

        for info in img_infos:
            xref  = info["xref"]
            w_px  = info["width"]
            h_px  = info["height"]
            bbox  = info["bbox"]

            # Apenas imagens inline pequenas (altura ≤ 2× linha de texto normal)
            if h_px > 60 or w_px < 5:
                continue

            smask = xref_to_smask.get(xref, 0)
            if smask <= 0:
                continue

            # OCR via smask (cacheia por xref)
            if xref not in ocr_cache:
                try:
                    mask_data = doc.extract_image(smask)
                    pil_mask = PILImage.open(io.BytesIO(mask_data["image"]))
                    ocr_cache[xref] = _ocr_image(pil_mask, inline=True)
                except Exception:
                    ocr_cache[xref] = ""

            ocr_text = ocr_cache[xref]
            if not ocr_text:
                continue

            # Palavras na mesma linha (tolerância = 80% da altura da imagem em pts)
            x0, y0, x1, y1 = bbox
            y_mid = (y0 + y1) / 2
            tol   = (y1 - y0) * 0.8
            line_words = sorted(
                [w for w in words if abs((w[1] + w[3]) / 2 - y_mid) < tol],
                key=lambda w: w[0]
            )
            before = [w[4] for w in line_words if w[2] <= x0 + 2]
            if not before:
                continue

            # Âncora: últimas 2 palavras antes da imagem (contexto suficiente)
            anchor = " ".join(before[-2:])
            page_items.append((y_mid, x0, anchor, ocr_text))

        # Ordem top→bottom, left→right dentro da página
        page_items.sort(key=lambda t: (t[0], t[1]))
        injections.extend((a, o) for _, _, a, o in page_items)

    doc.close()

    count = 0
    search_start = 0

    for anchor, ocr_text in injections:
        idx = md_text.find(anchor, search_start)
        if idx == -1:
            idx = md_text.find(anchor, 0)  # fallback: busca desde início
        if idx == -1:
            continue

        insert_at = idx + len(anchor)
        snippet   = f"`{ocr_text}`"
        md_text   = md_text[:insert_at] + snippet + md_text[insert_at:]
        search_start = insert_at + len(snippet)
        count += 1

    return md_text, count


# ──────────────────────────────────────────────
# FASE 3: OCR FALLBACK VIA PYTESSERACT
# ──────────────────────────────────────────────

def _broken_char_ratio(text: str) -> float:
    """Calcula ratio de chars de substituição (encoding quebrado)."""
    if not text:
        return 0.0
    broken = text.count('�') + text.count('?') * (text.count('?') > len(text) * 0.02)
    return broken / max(len(text), 1)


def needs_ocr(md_text: str) -> bool:
    """Retorna True se o texto extraído parece ter encoding quebrado."""
    if not _pytesseract_ok:
        return False
    return _broken_char_ratio(md_text) >= OCR_BROKEN_THRESH


def ocr_pdf_pytesseract(pdf_path: str, num_pages: int) -> str:
    """OCR página por página com Tesseract PT. Retorna texto concatenado."""
    import fitz  # pymupdf — disponível como dep transitiva do Docling
    doc = fitz.open(pdf_path)
    pages_text = []
    mat = fitz.Matrix(2.0, 2.0)  # 144 dpi

    for page_num in range(doc.page_count):
        page = doc[page_num]
        pix = page.get_pixmap(matrix=mat)
        pil_img = PILImage.frombytes("RGB", [pix.width, pix.height], pix.samples)
        text = pytesseract.image_to_string(pil_img, lang=OCR_LANG, config="--psm 1")
        pages_text.append(f"<!-- Página {page_num + 1} -->\n{text.strip()}")

    doc.close()
    return "\n\n".join(pages_text)


# ──────────────────────────────────────────────
# EXTRAÇÃO PRINCIPAL
# ──────────────────────────────────────────────

def process_pdf(pdf_path: str, out_dir: str) -> bool:
    """Processa um único PDF e gera o .md correspondente."""
    filename = os.path.basename(pdf_path)
    safe_name = sanitize_filename(filename)
    category = detect_category(pdf_path)

    print(f"  📄 Processando: {filename}")

    try:
        # 1. Converter PDF → DoclingDocument (layout AI + tabelas + imagens)
        result = CONVERTER.convert(pdf_path)
        doc = result.document

        # 2. Montar metadados
        meta = {
            'titulo':  None,
            'autor':   None,
            'paginas': doc.num_pages(),
        }

        # 3. Exportar para Markdown
        md_text = doc.export_to_markdown()

        # 4. Fase 3: detectar encoding quebrado → re-OCR com Tesseract PT
        if needs_ocr(md_text):
            print(f"    ⚠ Encoding quebrado detectado — aplicando OCR Tesseract PT...")
            md_text = ocr_pdf_pytesseract(pdf_path, meta['paginas'])
            print(f"    🔡 OCR concluído ({meta['paginas']} págs)")

        # 5. Limpar markdown
        md_text = clean_markdown(md_text)

        # 6. Extrair imagens + OCR inline
        img_subdir = os.path.join(IMG_DIR, safe_name)
        img_count, ocr_results = extract_images_with_ocr(doc, img_subdir, safe_name)
        if img_count == 0:
            try:
                os.rmdir(img_subdir)
            except OSError:
                pass
        else:
            inline_hits = sum(1 for _, _, t, fig in ocr_results if t and not fig)
            fig_hits    = sum(1 for _, _, t, fig in ocr_results if t and fig)
            print(f"    → {img_count} figura(s) salva(s), {inline_hits} fórmula(s)/íon(s) inline com OCR, {fig_hits} figura(s) com texto")
            md_text = inject_ocr_into_markdown(md_text, ocr_results)

        # 7. Injetar fórmulas/íons inline via PyMuPDF (imagens que Docling não capturou)
        md_text, inline_count = _inject_inline_fitz_ocr(md_text, pdf_path)
        if inline_count:
            print(f"    → {inline_count} fórmula(s)/símbolo(s) inline injetado(s) via PyMuPDF")

        # 8. Montar cabeçalho + conteúdo
        header = build_header(filename, meta, category)
        full_md = header + md_text

        # 8. Salvar arquivo .md
        out_path = os.path.join(out_dir, f"{safe_name}.md")
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(full_md)

        print(f"    ✅ Salvo: {safe_name}.md ({meta['paginas']} págs)")
        return True

    except Exception as e:
        print(f"    ❌ Erro: {e}")
        return False


def main():
    print("=" * 60)
    print("  EXTRATOR PDF → MARKDOWN (Docling IBM + Tesseract PT)")
    print("  Base de Conhecimento — TPA P1")
    print("=" * 60)

    if _pytesseract_ok:
        print(f"  🔡 OCR Tesseract PT: ativo ({TESSDATA_PREFIX})")
    else:
        print("  ⚠ OCR Tesseract: inativo (pytesseract não instalado ou tesseract não encontrado)")

    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(IMG_DIR, exist_ok=True)

    pdf_files = []
    for root, dirs, files in os.walk(DOCS_DIR):
        for f in files:
            if f.lower().endswith('.pdf'):
                pdf_files.append(os.path.join(root, f))

    if not pdf_files:
        print(f"\n⚠ Nenhum PDF encontrado em: {DOCS_DIR}")
        return

    print(f"\n📂 Diretório fonte: {DOCS_DIR}")
    print(f"📁 Diretório saída: {OUT_DIR}")
    print(f"🔍 PDFs encontrados: {len(pdf_files)}")
    print("-" * 60)

    success = 0
    errors = 0

    for pdf_path in sorted(pdf_files):
        if process_pdf(pdf_path, OUT_DIR):
            success += 1
        else:
            errors += 1

    print("-" * 60)
    print(f"\n📊 Resultado Final:")
    print(f"   ✅ Convertidos: {success}")
    print(f"   ❌ Erros: {errors}")
    print(f"   📁 Saída em: {OUT_DIR}")
    print("=" * 60)


if __name__ == '__main__':
    main()

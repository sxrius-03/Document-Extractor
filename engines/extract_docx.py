"""
extract_docx.py — Extrator de DOCX para Markdown estruturado
Usa Docling (IBM) para preservar a hierarquia e o texto dos documentos.
Saída: arquivos .md prontos para uso como base de conhecimento do TPA.
"""

import os
import re
import sys

from docling.document_converter import DocumentConverter

# Forçar UTF-8 no console do Windows
sys.stdout.reconfigure(encoding='utf-8', errors='replace')


# ──────────────────────────────────────────────
# CONFIGURAÇÃO
# ──────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOCS_DIR = os.path.join(BASE_DIR, "docs")
OUT_DIR  = os.path.join(BASE_DIR, "md_out_docx")


def build_converter() -> DocumentConverter:
    """Cria e configura o DocumentConverter do Docling para DOCX/DOC."""
    # O default do DocumentConverter já suporta DOCX nativamente
    return DocumentConverter()


# Instanciar uma vez — carrega modelos na inicialização
CONVERTER = build_converter()

# ──────────────────────────────────────────────
# FUNÇÕES AUXILIARES
# ──────────────────────────────────────────────

def sanitize_filename(name: str) -> str:
    """Remove caracteres problemáticos do nome de arquivo, mantendo legibilidade."""
    name = re.sub(r'\.docx?$', '', name, flags=re.IGNORECASE)
    name = re.sub(r'[<>:"/\\|?*]', '_', name)
    name = re.sub(r'_+', '_', name)
    if len(name) > 120:
        name = name[:120]
    return name.strip('_ ')


def build_header(filename: str, category: str) -> str:
    """Gera o cabeçalho padronizado (Reference Card) para o Markdown."""
    header = f"""# {filename}

## 📑 Ficha de Referência
| Campo | Valor |
|-------|-------|
| **Arquivo** | `{filename}` |
| **Categoria** | {category} |

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
    md_text = re.sub(r'\n{4,}', '\n\n\n', md_text)
    md_text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', md_text)
    return md_text.strip()


# ──────────────────────────────────────────────
# EXTRAÇÃO PRINCIPAL
# ──────────────────────────────────────────────

def process_docx(docx_path: str, out_dir: str) -> bool:
    """Processa um único documento Word e gera o .md correspondente."""
    filename = os.path.basename(docx_path)
    safe_name = sanitize_filename(filename)
    category = detect_category(docx_path)

    print(f"  📄 Processando: {filename}")

    try:
        # 1. Converter DOCX/DOC → DoclingDocument
        result = CONVERTER.convert(docx_path)
        doc = result.document

        # 2. Exportar para Markdown
        md_text = doc.export_to_markdown()

        # 3. Limpar markdown
        md_text = clean_markdown(md_text)

        # 4. Montar cabeçalho + conteúdo
        header = build_header(filename, category)
        full_md = header + md_text

        # 5. Salvar arquivo .md
        out_path = os.path.join(out_dir, f"{safe_name}.md")
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(full_md)

        print(f"    ✅ Salvo: {safe_name}.md")
        return True

    except Exception as e:
        print(f"    ❌ Erro: {e}")
        return False


def main():
    print("=" * 60)
    print("  EXTRATOR DOC/DOCX → MARKDOWN (Docling IBM)")
    print("  Base de Conhecimento")
    print("=" * 60)

    os.makedirs(OUT_DIR, exist_ok=True)
    
    # Criar pasta fonte caso não exista
    if not os.path.exists(DOCS_DIR):
        os.makedirs(DOCS_DIR)
        print(f"\n📂 Pasta '{DOCS_DIR}' criada. Coloque seus arquivos .docx lá e rode novamente.")
        return

    docx_files = []
    for root, dirs, files in os.walk(DOCS_DIR):
        for f in files:
            if f.lower().endswith('.docx') or f.lower().endswith('.doc'):
                docx_files.append(os.path.join(root, f))

    if not docx_files:
        print(f"\n⚠ Nenhum documento (.doc ou .docx) encontrado em: {DOCS_DIR}")
        return

    print(f"\n📂 Diretório fonte: {DOCS_DIR}")
    print(f"📁 Diretório saída: {OUT_DIR}")
    print(f"🔍 Arquivos encontrados: {len(docx_files)}")
    print("-" * 60)

    success = 0
    errors = 0

    for docx_path in sorted(docx_files):
        if process_docx(docx_path, OUT_DIR):
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

"""
Local, fully offline RAG ingestion with section-level role tagging.

Fixes the same leak found in the original MongoDB build: a doc-level
Min-Role tag at the top of the file does NOT protect Executive-only
sections further down. This version detects role section headers
(Associates / Senior / Executive) as it walks each document and tags
every chunk with the role level active in that section, not the
blanket doc-level tag.
"""

import os
import re
import glob
from docx import Document
import chromadb
import ollama

DOCS_DIR = "docs"
CHROMA_DIR = "chroma_db"
COLLECTION_NAME = "policies"
CHUNK_SIZE = 500

# Role hierarchy, higher number = more restricted
ROLE_LEVEL = {"Associate": 1, "Senior": 2, "Executive": 3}

# Matches lines like "Associates (e.g. Sales Representatives...)"
# or "Executive (CEO, CFO, and direct reports)"
SECTION_HEADER_RE = re.compile(r"^(Associates?|Senior|Executive)\s*\(")

SCOPE_RE = re.compile(r"Zone=(\w+).*Min-Role=(\w+)")


def read_docx_paragraphs(path):
    doc = Document(path)
    return [p.text for p in doc.paragraphs if p.text.strip()]


def extract_doc_defaults(paragraphs):
    """Find the SCOPE line for a fallback zone and default role."""
    zone = "Unknown"
    default_role = "Associate"
    for text in paragraphs:
        match = SCOPE_RE.search(text)
        if match:
            zone = match.group(1)
            default_role = match.group(2)
            break
    return zone, default_role


def group_by_role_section(paragraphs, default_role):
    """
    Walk paragraphs in order. When a section header like
    'Senior (e.g. ...)' or 'Executive (...)' appears, switch the
    active role for everything after it, until the next header.
    Returns a list of (role, text_block) tuples.
    """
    groups = []
    current_role = default_role
    current_lines = []

    for text in paragraphs:
        header_match = SECTION_HEADER_RE.match(text)
        if header_match:
            if current_lines:
                groups.append((current_role, "\n".join(current_lines)))
                current_lines = []
            role_word = header_match.group(1).rstrip("s")
            current_role = role_word if role_word in ROLE_LEVEL else current_role

        current_lines.append(text)

    if current_lines:
        groups.append((current_role, "\n".join(current_lines)))

    return groups


def chunk_text(text, size=CHUNK_SIZE):
    chunks = []
    for i in range(0, len(text), size):
        chunk = text[i:i + size].strip()
        if chunk:
            chunks.append(chunk)
    return chunks


def main():
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass
    collection = client.create_collection(COLLECTION_NAME)

    files = glob.glob(os.path.join(DOCS_DIR, "*.docx"))
    print(f"Found {len(files)} docx files in {DOCS_DIR}/")

    total_chunks = 0
    for filepath in files:
        filename = os.path.basename(filepath)
        paragraphs = read_docx_paragraphs(filepath)
        zone, default_role = extract_doc_defaults(paragraphs)
        role_groups = group_by_role_section(paragraphs, default_role)

        file_chunk_count = 0
        for role, block_text in role_groups:
            for idx, chunk in enumerate(chunk_text(block_text)):
                response = ollama.embed(model="nomic-embed-text", input=chunk)
                embedding = response.embeddings[0]

                chunk_id = f"{filename}::{role}::chunk{file_chunk_count}"
                collection.add(
                    ids=[chunk_id],
                    embeddings=[embedding],
                    documents=[chunk],
                    metadatas=[{
                        "source": filename,
                        "zone": zone,
                        "min_role": role,
                        "min_role_level": ROLE_LEVEL.get(role, 1),
                    }],
                )
                file_chunk_count += 1
                total_chunks += 1

        print(f"  Ingested {filename}: {file_chunk_count} chunks, "
              f"roles seen: {sorted(set(r for r, _ in role_groups))}")

    print(f"\nDone. {total_chunks} total chunks embedded and stored in {CHROMA_DIR}/")


if __name__ == "__main__":
    main()

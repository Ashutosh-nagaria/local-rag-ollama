import glob
import os
import re
import time

import chromadb
import streamlit as st
from docx import Document
from openai import OpenAI

DOCS_DIR = "docs"
CHROMA_DIR = "hosted_chroma_db"
COLLECTION_NAME = "policies_openai"

CHUNK_SIZE = 500

EMBED_MODEL = "text-embedding-3-small"
CHAT_MODEL = "gpt-5-mini"

ROLE_LEVEL = {
    "Associate": 1,
    "Senior": 2,
    "Executive": 3,
}

SECTION_HEADER_RE = re.compile(
    r"^(Associates?|Senior|Executive)\s*\("
)

SCOPE_RE = re.compile(
    r"Zone=(\w+).*Min-Role=(\w+)"
)

st.set_page_config(
    page_title="DunderMifflin Policy RAG",
    page_icon="🔐",
    layout="wide",
)

api_key = st.secrets.get(
    "OPENAI_API_KEY",
    os.getenv("OPENAI_API_KEY"),
)

if not api_key:
    st.error("OPENAI_API_KEY is not configured.")
    st.stop()

client = OpenAI(api_key=api_key)


def read_docx_paragraphs(path):
    doc = Document(path)
    return [
        p.text
        for p in doc.paragraphs
        if p.text.strip()
    ]


def extract_doc_defaults(paragraphs):
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
    groups = []

    current_role = default_role
    current_lines = []

    for text in paragraphs:
        header_match = SECTION_HEADER_RE.match(text)

        if header_match:
            if current_lines:
                groups.append(
                    (
                        current_role,
                        "\n".join(current_lines),
                    )
                )
                current_lines = []

            role_word = header_match.group(1).rstrip("s")

            if role_word in ROLE_LEVEL:
                current_role = role_word

        current_lines.append(text)

    if current_lines:
        groups.append(
            (
                current_role,
                "\n".join(current_lines),
            )
        )

    return groups


def chunk_text(text, size=CHUNK_SIZE):
    chunks = []

    for i in range(0, len(text), size):
        chunk = text[i:i + size].strip()

        if chunk:
            chunks.append(chunk)

    return chunks


@st.cache_resource
def get_collection():
    db = chromadb.PersistentClient(
        path=CHROMA_DIR
    )

    try:
        collection = db.get_collection(
            COLLECTION_NAME
        )
    except Exception:
        collection = db.create_collection(
            COLLECTION_NAME
        )

    if collection.count() == 0:
        ingest_documents(collection)

    return collection


def ingest_documents(collection):
    files = glob.glob(
        os.path.join(DOCS_DIR, "*.docx")
    )

    if not files:
        raise RuntimeError(
            "No policy DOCX files were found."
        )

    total_chunks = 0

    for filepath in files:
        filename = os.path.basename(filepath)

        paragraphs = read_docx_paragraphs(
            filepath
        )

        zone, default_role = extract_doc_defaults(
            paragraphs
        )

        role_groups = group_by_role_section(
            paragraphs,
            default_role,
        )

        file_chunk_count = 0

        for role, block_text in role_groups:
            chunks = chunk_text(
                block_text
            )

            for chunk in chunks:
                response = client.embeddings.create(
                    model=EMBED_MODEL,
                    input=chunk,
                )

                embedding = response.data[0].embedding

                chunk_id = (
                    f"{filename}::"
                    f"{role}::"
                    f"chunk{file_chunk_count}"
                )

                collection.add(
                    ids=[chunk_id],
                    embeddings=[embedding],
                    documents=[chunk],
                    metadatas=[
                        {
                            "source": filename,
                            "zone": zone,
                            "min_role": role,
                            "min_role_level": ROLE_LEVEL.get(
                                role,
                                1,
                            ),
                        }
                    ],
                )

                file_chunk_count += 1
                total_chunks += 1


def retrieve(question, user_role, n_results=8):
    collection = get_collection()

    allowed_level = ROLE_LEVEL[user_role]

    start = time.perf_counter()

    response = client.embeddings.create(
        model=EMBED_MODEL,
        input=question,
    )

    query_embedding = response.data[0].embedding

    embedding_time = (
        time.perf_counter() - start
    )

    start = time.perf_counter()

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
    )

    retrieval_time = (
        time.perf_counter() - start
    )

    authorized = []
    blocked = []

    for document, metadata, distance in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        item = {
            "document": document,
            "metadata": metadata,
            "distance": distance,
        }

        required_level = metadata.get(
            "min_role_level",
            1,
        )

        if required_level <= allowed_level:
            authorized.append(item)
        else:
            blocked.append(item)

    return (
        authorized,
        blocked,
        embedding_time,
        retrieval_time,
    )


def generate_answer(
    question,
    user_role,
    authorized,
):
    if not authorized:
        return (
            "I don't have access to information "
            "that can answer that question."
        ), 0

    context_parts = []

    for item in authorized:
        metadata = item["metadata"]

        source = metadata.get(
            "source",
            "Unknown source",
        )

        zone = metadata.get(
            "zone",
            "Unknown zone",
        )

        minimum_role = metadata.get(
            "min_role",
            "Unknown role",
        )

        context_parts.append(
            "[Source: "
            + source
            + " | Zone: "
            + zone
            + " | Minimum role: "
            + minimum_role
            + "]\n"
            + item["document"]
        )

    context = "\n\n".join(
        context_parts
    )

    prompt = (
        "You are an internal DunderMifflin "
        "policy assistant.\n\n"
        "The user's role is: "
        + user_role
        + ".\n\n"
        "Answer ONLY from the authorized "
        "policy context below.\n"
        "Do not use outside knowledge.\n"
        "Do not invent or infer missing "
        "policy information.\n"
        "If the answer is not explicitly "
        "supported by the authorized context, "
        "say that the information is not "
        "available to this user.\n\n"
        "AUTHORIZED POLICY CONTEXT:\n"
        + context
        + "\n\nUSER QUESTION:\n"
        + question
        + "\n\nANSWER:"
    )

    start = time.perf_counter()

    response = client.responses.create(
        model=CHAT_MODEL,
        input=prompt,
    )

    generation_time = (
        time.perf_counter() - start
    )

    return (
        response.output_text,
        generation_time,
    )


st.title(
    "🔐 DunderMifflin Policy RAG"
)

st.caption(
    "Public demonstration | Hosted inference | "
    "Role-based authorization before generation"
)

with st.sidebar:
    st.header("Access Control")

    user_role = st.selectbox(
        "Your role",
        [
            "Associate",
            "Senior",
            "Executive",
        ],
    )

    st.divider()

    st.markdown("### Architecture")

    st.markdown(
        """
**Hosted demonstration**

- Streamlit
- OpenAI embeddings
- OpenAI generation
- ChromaDB
- Section-level ACL
"""
    )

    st.divider()

    st.markdown(
        "### Governance evaluation"
    )

    st.metric(
        "Local governance tests",
        "8/8",
    )

    st.caption(
        "The GitHub repository contains "
        "the fully local Ollama implementation."
    )


question = st.text_area(
    "Ask a policy question",
    placeholder=(
        "Example: What is the Associate "
        "travel budget in the Americas?"
    ),
    height=100,
)

ask = st.button(
    "Ask Policy",
    type="primary",
    use_container_width=True,
)

if ask:
    if not question.strip():
        st.warning(
            "Please enter a question."
        )
        st.stop()

    with st.spinner(
        "Retrieving policy context..."
    ):
        (
            authorized,
            blocked,
            embedding_time,
            retrieval_time,
        ) = retrieve(
            question,
            user_role,
        )

    with st.spinner(
        "Generating answer..."
    ):
        (
            answer,
            generation_time,
        ) = generate_answer(
            question,
            user_role,
            authorized,
        )

    total_time = (
        embedding_time
        + retrieval_time
        + generation_time
    )

    st.subheader("Answer")
    st.write(answer)

    st.divider()

    st.subheader(
        "Retrieval & Authorization"
    )

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "Retrieved",
            len(authorized)
            + len(blocked),
        )

    with col2:
        st.metric(
            "Authorized",
            len(authorized),
        )

    with col3:
        st.metric(
            "Blocked",
            len(blocked),
        )

    if blocked:
        with st.expander(
            "🔒 Blocked chunks"
        ):
            for item in blocked:
                metadata = item["metadata"]

                st.write(
                    "**"
                    + metadata.get(
                        "min_role",
                        "Unknown role",
                    )
                    + "** | "
                    + metadata.get(
                        "source",
                        "Unknown source",
                    )
                )

    if authorized:
        with st.expander(
            "✅ Authorized chunks"
        ):
            for item in authorized:
                metadata = item["metadata"]

                st.write(
                    "**"
                    + metadata.get(
                        "min_role",
                        "Unknown role",
                    )
                    + "** | "
                    + metadata.get(
                        "source",
                        "Unknown source",
                    )
                )

    st.divider()

    st.subheader("Performance")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Embedding",
            f"{embedding_time:.2f}s",
        )

    with col2:
        st.metric(
            "Retrieval",
            f"{retrieval_time:.2f}s",
        )

    with col3:
        st.metric(
            "Generation",
            f"{generation_time:.2f}s",
        )

    with col4:
        st.metric(
            "Total",
            f"{total_time:.2f}s",
        )

    st.caption(
        "Authorization is applied before "
        "policy context is sent to the "
        "generation model."
    )

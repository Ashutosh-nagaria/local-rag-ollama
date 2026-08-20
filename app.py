import time

import chromadb
import ollama
import streamlit as st

CHROMA_DIR = "chroma_db"
COLLECTION_NAME = "policies"
EMBED_MODEL = "nomic-embed-text"
CHAT_MODEL = "llama3.2:3b"

ROLE_LEVEL = {
    "Associate": 1,
    "Senior": 2,
    "Executive": 3,
}

st.set_page_config(
    page_title="DunderMifflin Local RAG",
    page_icon="🔐",
    layout="wide",
)


@st.cache_resource
def get_collection():
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    return client.get_collection(COLLECTION_NAME)


def retrieve(question, user_role, n_results=8):
    collection = get_collection()
    allowed_level = ROLE_LEVEL[user_role]

    start = time.perf_counter()

    embedding_response = ollama.embed(
        model=EMBED_MODEL,
        input=question,
    )

    embedding_time = time.perf_counter() - start

    start = time.perf_counter()

    results = collection.query(
        query_embeddings=[embedding_response.embeddings[0]],
        n_results=n_results,
    )

    retrieval_time = time.perf_counter() - start

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

        required_level = metadata.get("min_role_level", 1)

        if required_level <= allowed_level:
            authorized.append(item)
        else:
            blocked.append(item)

    return authorized, blocked, embedding_time, retrieval_time


def generate_answer(question, user_role, authorized):
    if not authorized:
        return "I don't have access to information that can answer that question.", 0

    context_parts = []

    for item in authorized:
        metadata = item["metadata"]

        source = metadata.get("source", "Unknown source")
        zone = metadata.get("zone", "Unknown zone")
        minimum_role = metadata.get("min_role", "Unknown role")
        document = item["document"]

        context_parts.append(
            "[Source: "
            + source
            + " | Zone: "
            + zone
            + " | Minimum role: "
            + minimum_role
            + "]\n"
            + document
        )

    context = "\n\n".join(context_parts)

    prompt = (
        "You are an internal DunderMifflin policy assistant.\n\n"
        "The user's role is: "
        + user_role
        + ".\n\n"
        "Answer ONLY from the authorized policy context below.\n"
        "Do not use outside knowledge.\n"
        "Do not invent or infer missing policy information.\n"
        "If the answer is not explicitly supported by the authorized context, "
        "say that the information is not available to this user.\n\n"
        "AUTHORIZED POLICY CONTEXT:\n"
        + context
        + "\n\nUSER QUESTION:\n"
        + question
        + "\n\nANSWER:"
    )

    start = time.perf_counter()

    response = ollama.chat(
        model=CHAT_MODEL,
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
    )

    generation_time = time.perf_counter() - start

    return response.message.content, generation_time


st.title("🔐 DunderMifflin Local Policy RAG")
st.caption("Fully local RAG with role-based authorization")

with st.sidebar:
    st.header("Access Control")

    user_role = st.selectbox(
        "Your role",
        ["Associate", "Senior", "Executive"],
    )

    st.divider()

    st.markdown("### Architecture")
    st.markdown(
        """
**Local only**

- Ollama
- llama3.2:3b
- nomic-embed-text
- ChromaDB
- Section-level ACL
"""
    )

    st.divider()

    st.markdown("### Governance evaluation")
    st.metric("Local governance tests", "8/8")
    st.caption(
        "Separate cloud MCP evaluation: 39/39. "
        "These are separate test suites, not a direct benchmark comparison."
    )


question = st.text_area(
    "Ask a policy question",
    placeholder="Example: What is the Executive compensation band in the Americas?",
    height=100,
)

ask = st.button(
    "Ask Policy",
    type="primary",
    use_container_width=True,
)

if ask:
    if not question.strip():
        st.warning("Please enter a question.")
        st.stop()

    with st.spinner("Retrieving authorized policy context..."):
        (
            authorized,
            blocked,
            embedding_time,
            retrieval_time,
        ) = retrieve(question, user_role)

    with st.spinner("Generating answer locally..."):
        answer, generation_time = generate_answer(
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

    st.subheader("Retrieval & Authorization")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Retrieved", len(authorized) + len(blocked))

    with col2:
        st.metric("Authorized", len(authorized))

    with col3:
        st.metric("Blocked", len(blocked))

    if blocked:
        with st.expander("🔒 Blocked chunks"):
            for item in blocked:
                metadata = item["metadata"]
                st.write(
                    "**"
                    + metadata.get("min_role", "Unknown role")
                    + "** | "
                    + metadata.get("source", "Unknown source")
                )

    if authorized:
        with st.expander("✅ Authorized chunks"):
            for item in authorized:
                metadata = item["metadata"]
                st.write(
                    "**"
                    + metadata.get("min_role", "Unknown role")
                    + "** | "
                    + metadata.get("source", "Unknown source")
                )

    st.divider()

    st.subheader("Performance")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Embedding", f"{embedding_time:.2f}s")

    with col2:
        st.metric("Retrieval", f"{retrieval_time:.2f}s")

    with col3:
        st.metric("Generation", f"{generation_time:.2f}s")

    with col4:
        st.metric("Total", f"{total_time:.2f}s")

    st.caption(
        "All embeddings, retrieval, authorization, and generation run locally "
        "through Ollama and ChromaDB."
    )

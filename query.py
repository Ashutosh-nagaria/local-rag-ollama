import time
import chromadb
import ollama

CHROMA_DIR = "chroma_db"
COLLECTION_NAME = "policies"
EMBED_MODEL = "nomic-embed-text"
LLM_MODEL = "llama3.2:3b"

ROLE_LEVEL = {
    "Associate": 1,
    "Senior": 2,
    "Executive": 3,
}


def retrieve(question, user_role, n_results=8):
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    collection = client.get_collection(COLLECTION_NAME)

    start = time.perf_counter()

    embedding_response = ollama.embed(
        model=EMBED_MODEL,
        input=question,
    )

    embedding_time = time.perf_counter() - start
    question_embedding = embedding_response.embeddings[0]

    start = time.perf_counter()

    results = collection.query(
        query_embeddings=[question_embedding],
        n_results=n_results,
    )

    retrieval_time = time.perf_counter() - start

    allowed_level = ROLE_LEVEL[user_role]

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

        chunk_role_level = metadata.get("min_role_level", 1)

        if chunk_role_level <= allowed_level:
            authorized.append(item)
        else:
            blocked.append(item)

    return authorized, blocked, embedding_time, retrieval_time


def generate_answer(question, user_role, retrieved_chunks):
    if not retrieved_chunks:
        return (
            "I don't have access to information that can answer "
            "that question."
        ), 0

    context_parts = []

    for item in retrieved_chunks:
        metadata = item["metadata"]

        context_parts.append(
            f"[Source: {metadata['source']} | "
            f"Zone: {metadata['zone']} | "
            f"Minimum role: {metadata['min_role']}]\n"
            f"{item['document']}"
        )

    context = "\n\n".join(context_parts)

    prompt = f"""You are an internal DunderMifflin policy assistant.

The user has the role: {user_role}.

Answer the user's question using ONLY the authorized policy context below.

IMPORTANT INSTRUCTIONS:
- Find the policy section that most directly answers the question.
- Match the requested region, policy topic, and employee role exactly.
- The context may contain information from other regions and roles. Ignore those when they do not match the question.
- If the exact answer appears in the context, state it directly and clearly.
- Do not claim information is missing when the requested fact is explicitly present in the context.
- Do not invent or infer facts that are not present.
- If the requested fact genuinely does not appear in the authorized context, say that it is not available to this user.

USER QUESTION:
{question}

AUTHORIZED POLICY CONTEXT:
{context}
"""

    start = time.perf_counter()

    response = ollama.chat(
        model=LLM_MODEL,
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
    )

    generation_time = time.perf_counter() - start

    return response.message.content, generation_time


def main():
    print("Local DunderMifflin RAG")
    print("======================")

    user_role = input(
        "User role (Associate/Senior/Executive): "
    ).strip()

    if user_role not in ROLE_LEVEL:
        print("Invalid role.")
        return

    question = input("Question: ").strip()

    total_start = time.perf_counter()

    (
        authorized,
        blocked,
        embedding_time,
        retrieval_time,
    ) = retrieve(question, user_role)

    answer, generation_time = generate_answer(
        question,
        user_role,
        authorized,
    )

    total_time = time.perf_counter() - total_start

    print(f"\nRetrieved candidates: {len(authorized) + len(blocked)}")
    print(f"Authorized chunks: {len(authorized)}")
    print(f"Blocked chunks: {len(blocked)}")

    if authorized:
        print("\nAUTHORIZED ROLES:")
        for item in authorized:
            print(
                f"  {item['metadata']['min_role']} "
                f"({item['metadata']['source']})"
            )

    if blocked:
        print("\nBLOCKED ROLES:")
        for item in blocked:
            print(
                f"  {item['metadata']['min_role']} "
                f"({item['metadata']['source']})"
            )

    print("\nTIMING")
    print("------")
    print(f"Embedding:  {embedding_time:.2f}s")
    print(f"Retrieval:  {retrieval_time:.2f}s")
    print(f"Generation: {generation_time:.2f}s")
    print(f"Total:      {total_time:.2f}s")

    print("\nANSWER")
    print("------")
    print(answer)


if __name__ == "__main__":
    main()

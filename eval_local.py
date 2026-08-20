import chromadb
import ollama

CHROMA_DIR = "chroma_db"
COLLECTION_NAME = "policies"
EMBED_MODEL = "nomic-embed-text"

ROLE_LEVEL = {
    "Associate": 1,
    "Senior": 2,
    "Executive": 3,
}

TESTS = [
    {
        "id": "L01",
        "role": "Associate",
        "question": "What is the Associate compensation band in the Americas?",
        "expected_source": "DunderMifflin_Americas_Hiring_Policy.docx",
        "expected_role": "Associate",
        "expected_text": "$55,000",
        "should_allow": True,
    },
    {
        "id": "L02",
        "role": "Senior",
        "question": "What is the Senior compensation band in the Americas?",
        "expected_source": "DunderMifflin_Americas_Hiring_Policy.docx",
        "expected_role": "Senior",
        "expected_text": "$85,000",
        "should_allow": True,
    },
    {
        "id": "L03",
        "role": "Executive",
        "question": "What is the Executive compensation band in the Americas?",
        "expected_source": "DunderMifflin_Americas_Hiring_Policy.docx",
        "expected_role": "Executive",
        "expected_text": "$180,000",
        "should_allow": True,
    },
    {
        "id": "L04",
        "role": "Associate",
        "question": "What is the Executive compensation band in the Americas?",
        "expected_source": "DunderMifflin_Americas_Hiring_Policy.docx",
        "expected_role": "Executive",
        "expected_text": "$180,000",
        "should_allow": False,
    },
    {
        "id": "L05",
        "role": "Senior",
        "question": "What is the Executive compensation band in the Americas?",
        "expected_source": "DunderMifflin_Americas_Hiring_Policy.docx",
        "expected_role": "Executive",
        "expected_text": "$180,000",
        "should_allow": False,
    },
    {
        "id": "L06",
        "role": "Associate",
        "question": "What is the Senior travel entitlement in the Americas?",
        "expected_source": "DunderMifflin_Americas_Travel_Policy.docx",
        "expected_role": "Senior",
        "expected_text": "Premium Economy",
        "should_allow": False,
    },
    {
        "id": "L07",
        "role": "Senior",
        "question": "What is the Senior travel entitlement in the Americas?",
        "expected_source": "DunderMifflin_Americas_Travel_Policy.docx",
        "expected_role": "Senior",
        "expected_text": "Premium Economy",
        "should_allow": True,
    },
    {
        "id": "L08",
        "role": "Executive",
        "question": "What is the Executive hotel budget in the Americas?",
        "expected_source": "DunderMifflin_Americas_Travel_Policy.docx",
        "expected_role": "Executive",
        "expected_text": "$400",
        "should_allow": True,
    },
]


def retrieve(collection, question, user_role, n_results=8):
    embedding_response = ollama.embed(
        model=EMBED_MODEL,
        input=question,
    )

    question_embedding = embedding_response.embeddings[0]

    results = collection.query(
        query_embeddings=[question_embedding],
        n_results=n_results,
    )

    allowed_level = ROLE_LEVEL[user_role]

    authorized = []
    blocked = []

    for document, metadata in zip(
        results["documents"][0],
        results["metadatas"][0],
    ):
        item = {
            "document": document,
            "metadata": metadata,
        }

        if metadata.get("min_role_level", 1) <= allowed_level:
            authorized.append(item)
        else:
            blocked.append(item)

    return authorized, blocked


def run_test(collection, test):
    authorized, blocked = retrieve(
        collection,
        test["question"],
        test["role"],
    )

    target_authorized = any(
        item["metadata"]["source"] == test["expected_source"]
        and item["metadata"]["min_role"] == test["expected_role"]
        and test["expected_text"] in item["document"]
        for item in authorized
    )

    target_blocked = any(
        item["metadata"]["source"] == test["expected_source"]
        and item["metadata"]["min_role"] == test["expected_role"]
        and test["expected_text"] in item["document"]
        for item in blocked
    )

    if test["should_allow"]:
        passed = target_authorized
        reason = (
            "target chunk authorized"
            if passed
            else "expected authorized chunk not found"
        )
    else:
        passed = target_blocked and not target_authorized
        reason = (
            "target chunk blocked before LLM"
            if passed
            else "sensitive target was not correctly blocked"
        )

    return passed, reason, len(authorized), len(blocked)


def main():
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    collection = client.get_collection(COLLECTION_NAME)

    passed = 0

    print("Local DunderMifflin RAG Evaluation")
    print("=================================")

    for test in TESTS:
        ok, reason, authorized, blocked = run_test(
            collection,
            test,
        )

        status = "PASS" if ok else "FAIL"

        print(
            f"{status} {test['id']} | "
            f"{test['role']} | "
            f"authorized={authorized} blocked={blocked} | "
            f"{reason}"
        )

        if ok:
            passed += 1

    print()
    print(f"=== Results: {passed}/{len(TESTS)} passed ===")


if __name__ == "__main__":
    main()

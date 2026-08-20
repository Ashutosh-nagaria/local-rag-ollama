Absolutely. Here is the **complete `CONCEPTS.md` file**. Copy everything inside the code block into `CONCEPTS.md`.

markdown
# Concepts

A plain-language explanation of the concepts behind the DunderMifflin Policy RAG system.

## 1. What is RAG?

RAG stands for Retrieval-Augmented Generation.

Instead of asking a language model to answer entirely from what it learned during training, a RAG system first retrieves relevant information from a knowledge source and then gives that information to the model.

Simple version:

Question
   |
   v
Find relevant information
   |
   v
Give information to model
   |
   v
Generate answer

This is useful for enterprise policies because the answer should come from the organization's documents rather than from general model knowledge.

## 2. Why use RAG?

A language model may know general information, but it does not automatically know the contents of a company's internal documents.

RAG gives the model access to a controlled knowledge source at query time.

For this project, the knowledge source is a collection of DunderMifflin policy documents.

## 3. What is chunking?

Large documents are divided into smaller pieces called chunks.

For this project, policy content is divided into approximately 500-character chunks.

Instead of searching an entire document, the system searches these smaller pieces.

This improves retrieval because the system can identify the specific part of a policy that is relevant to the question.

## 4. What is an embedding?

An embedding is a numerical representation of text.

For example:

"What is the travel budget?"

is converted into a vector containing many numbers.

The vector represents aspects of the meaning of the text.

Another sentence with similar meaning should produce a vector that is relatively close to it.

This allows semantic search.

## 5. What is semantic search?

Traditional keyword search looks for matching words.

Semantic search looks for similar meaning.

For example:

Question:

"How much can an Associate spend on business travel?"

Policy:

"Associates receive an annual travel allowance of $8,000."

The wording is different, but the meaning is related.

Embeddings allow the system to identify this relationship.

## 6. What is ChromaDB?

ChromaDB is the vector database used by this project.

It stores:

Policy chunk
+
Embedding
+
Metadata

The metadata includes authorization information such as:

Source
Region
Minimum role
Role level

When a user asks a question, the question is converted into an embedding and ChromaDB finds the most similar stored policy chunks.

## 7. What is Ollama?

Ollama is the local runtime used to run AI models.

It allows the application to run models directly on the local machine instead of sending model inference requests to a hosted model provider.

In this project, Ollama runs two different models.

## 8. What is nomic-embed-text?

nomic-embed-text is the embedding model used by the local implementation.

Its job is to convert text into vectors.

It is used for both:

1. Policy documents during ingestion.
2. User questions during retrieval.

The same embedding space allows the question vector to be compared with the policy vectors stored in ChromaDB.

It does not generate the final answer.

## 9. What is llama3.2:3b?

llama3.2:3b is the language model used for generation in the local implementation.

After retrieval and authorization, it receives:

User question
+
Authorized policy context

It then generates the final response.

## 10. Why are there two models?

The two models have different jobs.

nomic-embed-text

    |
    v

Understand text as vectors

    |
    v

Semantic retrieval

while:

llama3.2:3b

    |
    v

Read authorized context

    |
    v

Generate answer

Ollama provides the local runtime for both.

## 11. What is authorization?

Authorization determines what an already-identified user is allowed to access.

This project uses three roles:

Associate = 1
Senior = 2
Executive = 3

Each policy chunk has a minimum required role.

The application compares:

User role level
        vs.
Chunk minimum role level

If:

chunk level <= user level

the chunk is authorized.

Otherwise it is blocked.

## 12. Why section-level authorization?

A single policy document can contain multiple role sections.

For example:

Associate section
Senior section
Executive section

A document-level permission cannot accurately represent those boundaries.

If the entire document were marked Executive-only, Associates could not access legitimate Associate information.

If the entire document were marked Associate-accessible, restricted Executive information could potentially become visible.

The ingestion pipeline therefore identifies role section headers and assigns the appropriate authorization metadata to each chunk.

## 13. Why authorization happens before generation

This is the central security principle of the project.

A weak design might retrieve everything and then tell the language model:

"Do not reveal anything the user isn't allowed to see."

That makes the model part of the security boundary.

This project uses a stronger design:

Retrieve
   |
   v
Authorize
   |
   +---- Block restricted chunks
   |
   v
Authorized context
   |
   v
Generate

The model never receives the blocked policy content.

This makes authorization a deterministic application-level control rather than a prompting instruction.

## 14. What happens during ingestion?

The ingestion pipeline works approximately like this:

DOCX policy
    |
    v
Read paragraphs
    |
    v
Identify role sections
    |
    v
Split into chunks
    |
    v
Generate embeddings
    |
    v
Store in ChromaDB

Each chunk receives metadata describing its authorization requirements.

## 15. What happens when a user asks a question?

The runtime flow is:

User question
      |
      v
Create question embedding
      |
      v
ChromaDB semantic search
      |
      v
Retrieve relevant chunks
      |
      v
Check role authorization
      |
      +---- Block unauthorized chunks
      |
      v
Authorized policy context
      |
      v
Language model
      |
      v
Answer

## 16. Local versus hosted deployment

The repository's local implementation uses:

Ollama
├── nomic-embed-text
└── llama3.2:3b

ChromaDB
+
Python authorization logic

The public Streamlit demonstration uses:

OpenAI embeddings
+
ChromaDB
+
Python authorization logic
+
OpenAI generation

The hosted demonstration uses OpenAI because Streamlit Community Cloud does not provide the local Ollama runtime used by the fully local implementation.

The underlying architectural principle remains the same:

Retrieve
   |
Authorize
   |
Generate

## 17. Why not let the language model handle authorization?

Language models are probabilistic systems.

Authorization should be deterministic.

A security decision should not depend on whether a model correctly follows an instruction such as:

"Do not reveal Executive information."

Instead, the application removes unauthorized information before the model receives it.

That creates a clearer security boundary.

## 18. What does the evaluation test?

The local evaluation contains 8 governance scenarios.

The tests verify both:

- Information that the user should be able to access.
- Information that the user should not be able to access.

The current result is:

8/8 passed

The important part of the denial tests is that restricted chunks are blocked before generation.

## 19. What does this project demonstrate?

The project demonstrates several ideas working together:

RAG
+
Semantic retrieval
+
Vector database
+
Local model inference
+
Role-based authorization
+
Section-level access control
+
Governance evaluation

The central lesson is:

> A useful enterprise AI system needs both retrieval and authorization.

Finding the right information is not enough.

The system must also determine whether the current user is allowed to receive that information.

## 20. Production considerations

This project is a demonstration rather than a production authorization platform.

A production system would need additional capabilities such as:

- Identity integration
- Authentication
- Centralized authorization policies
- Audit logs
- Encryption
- Document lifecycle management
- Monitoring
- Evaluation at larger scale
- Model and dependency management
- Secret management
- Operational controls

The purpose of this project is to demonstrate the core architectural principle clearly and reproducibly.

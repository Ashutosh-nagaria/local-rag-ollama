Yes. Let's make the public documentation **clean, technical, and evergreen**.

Replace your **README.md** with this:

````markdown
# DunderMifflin Local Policy RAG

A governance-aware Retrieval-Augmented Generation (RAG) system for enterprise policy questions.

The project demonstrates how role-based authorization can be enforced at the retrieval layer so that restricted policy content is removed before it reaches the language model.

## Live demonstration

[Open the live Streamlit demo](https://local-rag-ollama.streamlit.app/)

The repository contains the fully local implementation using:

- Ollama
- llama3.2:3b
- nomic-embed-text
- ChromaDB
- Python
- Streamlit

The live Streamlit demonstration uses OpenAI APIs for hosted embeddings and generation because Streamlit Community Cloud does not provide the local Ollama runtime.

The retrieval and authorization flow remains application-controlled in the hosted demonstration.

## What this project demonstrates

A conventional RAG system answers:

> "What information is relevant to this question?"

An enterprise RAG system also needs to answer:

> "Is this user allowed to see that information?"

This project treats authorization as part of the retrieval pipeline rather than relying on the language model to decide what a user can access.

The core flow is:

```text
Policy documents
      |
      v
Chunking + role metadata
      |
      v
Embeddings
      |
      v
ChromaDB
      |
      v
Semantic retrieval
      |
      v
Role-based authorization
      |
      +---- Unauthorized chunks blocked
      |
      v
Authorized context
      |
      v
Language model
      |
      v
Answer
````

## Key security design

Each policy chunk contains authorization metadata including:

* Source document
* Region / zone
* Minimum required role
* Numeric role level

The role hierarchy is:

```text
Associate = 1
Senior    = 2
Executive = 3
```

A chunk is authorized when:

```text
chunk minimum role level <= user's role level
```

For example:

```text
Associate user
    |
    +-- Associate chunk  -> ALLOW
    +-- Senior chunk     -> BLOCK
    +-- Executive chunk  -> BLOCK
```

The authorization decision happens before generation.

The language model therefore receives only the policy context that the application has already authorized.

## Why section-level authorization matters

The original policy documents contain multiple role sections inside the same document.

A document-level permission is therefore too coarse.

For example, a single policy document can contain:

```text
Associate section
Senior section
Executive section
```

Giving the entire document an Executive permission would incorrectly protect or expose the document as a whole.

The ingestion pipeline instead detects role section headers and assigns the active role to each chunk.

This makes the authorization boundary match the actual policy content boundary.

## Local architecture

The fully local implementation runs on the local machine.

```text
                    Local machine

                         Ollama
                       /       \
                      /         \
                     v           v
          nomic-embed-text   llama3.2:3b
               |                  |
               v                  |
           ChromaDB               |
               |                  |
               v                  |
        Role authorization        |
               |                  |
               +------------------+
                        |
                      Answer
```

### Ollama

Ollama is the local runtime used to run the AI models.

It provides the interface through which the application calls the local models.

### nomic-embed-text

This is the local embedding model.

It converts policy text and user questions into numerical vectors.

These vectors allow semantically similar questions and policy chunks to be matched.

It does not generate the final answer.

### llama3.2:3b

This is the local language model used to generate the final answer.

It receives the user's question and the authorized policy context.

### ChromaDB

ChromaDB is the local vector database.

It stores:

* Policy chunks
* Embeddings
* Authorization metadata

It performs semantic similarity retrieval against the stored embeddings.

## Hosted demonstration architecture

The live Streamlit demonstration uses hosted inference:

```text
User question
      |
      v
OpenAI embeddings
      |
      v
ChromaDB
      |
      v
Role-based authorization
      |
      +---- Unauthorized chunks blocked
      |
      v
Authorized context
      |
      v
OpenAI generation
      |
      v
Answer
```

The hosted version uses OpenAI for:

1. Creating embeddings for the policy chunks and user questions.
2. Generating the final natural-language answer.

ChromaDB and the application's authorization logic remain separate from the language model.

This separation demonstrates that access control does not need to be delegated to the model provider.

## Evaluation

The local governance evaluation passes all 8 scenarios:

```text
8/8 passed
```

The evaluation covers both:

* Authorized retrieval
* Unauthorized retrieval

In denial scenarios, the target restricted chunk is verified as blocked before generation.

The project also has a separate cloud MCP evaluation with:

```text
39/39 passed
```

These are separate evaluation suites and should not be interpreted as a direct benchmark comparison.

## Example behavior

### Authorized

An Associate asking for the Americas Associate travel budget can receive:

```text
$8,000 per year
```

### Restricted

An Associate asking for Executive compensation does not receive the Executive compensation information.

The restricted chunks are removed before generation.

### Executive

An Executive asking for Executive compensation can receive the authorized Executive policy information:

```text
$180,000–$350,000 base annually,
plus bonus and equity per grade.
```

## Run locally

### Requirements

* Python 3
* Ollama
* Sufficient local hardware to run the selected models

### 1. Clone the repository

```bash
git clone https://github.com/Ashutosh-nagaria/local-rag-ollama.git
cd local-rag-ollama
```

### 2. Install the Ollama models

```bash
ollama pull llama3.2:3b
ollama pull nomic-embed-text
```

Make sure Ollama is running.

### 3. Create a Python environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 4. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 5. Ingest the policies

```bash
python3 ingest.py
```

This reads the policy documents, creates role-aware chunks, generates local embeddings, and stores them in ChromaDB.

### 6. Run the command-line interface

```bash
python3 query.py
```

### 7. Run the governance evaluation

```bash
python3 eval_local.py
```

Expected result:

```text
=== Results: 8/8 passed ===
```

### 8. Run Streamlit locally

```bash
streamlit run app.py
```

For the fully local implementation, the application uses Ollama for both embeddings and generation.

## Project structure

```text
local-rag-ollama/
├── app.py
├── ingest.py
├── query.py
├── eval_local.py
├── requirements.txt
├── README.md
├── CONCEPTS.md
├── .gitignore
└── docs/
    ├── APAC policies
    ├── Americas policies
    └── Europe policies
```

Generated runtime data such as the local virtual environment and ChromaDB storage are excluded from the repository.

## Limitations

This is a portfolio-scale demonstration rather than a production enterprise authorization platform.

A production implementation would additionally require considerations such as:

* Identity and authentication integration
* Centralized authorization policy management
* Audit logging
* Encryption
* Document versioning
* Monitoring and alerting
* Larger evaluation suites
* Production model serving
* Key and secret management
* Operational controls

The project intentionally focuses on demonstrating the architectural principle of enforcing authorization before sensitive context reaches the language model.

## Why it matters

The central idea is simple:

> Retrieval answers "what is relevant?"

> Authorization answers "what is allowed?"

Enterprise RAG needs both.

The language model should not be the security boundary.

The application should determine what context the model is allowed to receive.

## Built by Ashutosh

A practical exploration of local AI, enterprise RAG, and governance-aware system design.

````

And for **`CONCEPTS.md`**, use this:

```markdown
# Concepts

A plain-language explanation of the concepts behind the DunderMifflin Policy RAG system.

## 1. What is RAG?

RAG stands for Retrieval-Augmented Generation.

Instead of asking a language model to answer entirely from what it learned during training, a RAG system first retrieves relevant information from a knowledge source and then gives that information to the model.

Simple version:

```text
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
````

This is useful for enterprise policies because the answer should come from the organization's current documents rather than from general model knowledge.

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

```text
"What is the travel budget?"
```

is converted into a vector containing many numbers.

The vector represents aspects of the meaning of the text.

Another sentence with similar meaning should produce a vector that is relatively close to it.

This allows semantic search.

## 5. What is semantic search?

Traditional keyword search looks for matching words.

Semantic search looks for similar meaning.

For example:

```text
Question:
"How much can an Associate spend on business travel?"

Policy:
"Associates receive an annual travel allowance of $8,000."
```

The wording is different, but the meaning is related.

Embeddings allow the system to identify this relationship.

## 6. What is ChromaDB?

ChromaDB is the vector database used by this project.

It stores:

```text
Policy chunk
+
Embedding
+
Metadata
```

The metadata includes authorization information such as:

```text
Source
Region
Minimum role
Role level
```

When a user asks a question, the question is converted into an embedding and ChromaDB finds the most similar stored policy chunks.

## 7. What is Ollama?

Ollama is the local runtime used to run AI models.

It allows the application to run models directly on the local machine instead of sending model inference requests to a hosted model provider.

In this project, Ollama runs two different models.

## 8. What is nomic-embed-text?

`nomic-embed-text` is the embedding model used by the local implementation.

Its job is to convert text into vectors.

It is used for both:

1. Policy documents during ingestion.
2. User questions during retrieval.

The same embedding space allows the question vector to be compared with the policy vectors stored in ChromaDB.

It does not generate the final answer.

## 9. What is llama3.2:3b?

`llama3.2:3b` is the language model used for generation in the local implementation.

After retrieval and authorization, it receives:

```text
User question
+
Authorized policy context
```

It then generates the final response.

## 10. Why are there two models?

The two models have different jobs.

```text
nomic-embed-text
        |
        v
Understand text as vectors
        |
        v
Semantic retrieval
```

while:

```text
llama3.2:3b
        |
        v
Read authorized context
        |
        v
Generate answer
```

Ollama provides the local runtime for both.

## 11. What is authorization?

Authorization determines what an already-identified user is allowed to access.

This project uses three roles:

```text
Associate = 1
Senior    = 2
Executive = 3
```

Each policy chunk has a minimum required role.

The application compares:

```text
User role level
        vs.
Chunk minimum role level
```

If:

```text
chunk level <= user level
```

the chunk is authorized.

Otherwise it is blocked.

## 12. Why section-level authorization?

A single policy document can contain multiple role sections.

For example:

```text
Associate section
Senior section
Executive section
```

A document-level permission cannot accurately represent those boundaries.

If the entire document were marked Executive-only, Associates could not access legitimate Associate information.

If the entire document were marked Associate-accessible, restricted Executive information could potentially become visible.

The ingestion pipeline therefore identifies role section headers and assigns the appropriate authorization metadata to each chunk.

## 13. Why authorization happens before generation

This is the central security principle of the project.

A weak design might retrieve everything and then tell the language model:

> "Don't reveal anything the user isn't allowed to see."

That makes the model part of the security boundary.

This project uses a stronger design:

```text
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
```

The model never receives the blocked policy content.

This makes authorization a deterministic application-level control rather than a prompting instruction.

## 14. What happens during ingestion?

The ingestion pipeline works approximately like this:

```text
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
```

Each chunk receives metadata describing its authorization requirements.

## 15. What happens when a user asks a question?

The runtime flow is:

```text
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
```

## 16. Local versus hosted deployment

The repository's local implementation uses:

```text
Ollama
├── nomic-embed-text
└── llama3.2:3b

ChromaDB
+
Python authorization logic
```

The public Streamlit demonstration uses:

```text
OpenAI embeddings
+
ChromaDB
+
Python authorization logic
+
OpenAI generation
```

The hosted demonstration uses OpenAI because Streamlit Community Cloud does not provide the local Ollama runtime used by the fully local implementation.

The underlying architectural principle remains the same:

```text
Retrieve
   |
Authorize
   |
Generate
```

## 17. Why not let the language model handle authorization?

Language models are probabilistic systems.

Authorization should be deterministic.

A security decision should not depend on whether a model correctly follows an instruction such as:

> "Do not reveal Executive information."

Instead, the application removes unauthorized information before the model receives it.

That creates a clearer security boundary.

## 18. What does the evaluation test?

The local evaluation contains 8 governance scenarios.

The tests verify both:

* Information that the user should be able to access.
* Information that the user should not be able to access.

The current result is:

```text
8/8 passed
```

The important part of the denial tests is that restricted chunks are blocked before generation.

## 19. What does this project demonstrate?

The project demonstrates several ideas working together:

```text
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
```

The central lesson is:

> A useful enterprise AI system needs both retrieval and authorization.

Finding the right information is not enough.

The system must also determine whether the current user is allowed to receive that information.

## 20. Production considerations

This project is a demonstration rather than a production authorization platform.

A production system would need additional capabilities such as:

* Identity integration
* Authentication
* Centralized authorization policies
* Audit logs
* Encryption
* Document lifecycle management
* Monitoring
* Evaluation at larger scale
* Model and dependency management
* Secret management
* Operational controls

The purpose of this project is to demonstrate the core architectural principle clearly and reproducibly.
Ashutosh :)

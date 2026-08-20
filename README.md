Absolutely. Here is the **entire final `README.md` in one single block**, with nothing omitted.

Copy everything inside this block and replace your existing `README.md`:


# DunderMifflin Local Policy RAG

A governance-aware Retrieval-Augmented Generation (RAG) system for enterprise policy questions.

The project demonstrates how role-based authorization can be enforced before sensitive policy context reaches a language model.

## Live demo

**[Try the live Streamlit demo](https://local-rag-ollama.streamlit.app/)**

This project can be run completely locally using Ollama, `llama3.2:3b`, `nomic-embed-text`, and ChromaDB.

For a convenient live demonstration, I have also hosted the application on Streamlit Community Cloud. The hosted demonstration uses OpenAI APIs for embeddings and generation because the Streamlit environment does not provide the local Ollama runtime.

The retrieval pipeline and section-level authorization logic remain application-controlled in the hosted demonstration.

**Local implementation:** Ollama + local models + ChromaDB  
**Live demonstration:** Streamlit + OpenAI APIs + ChromaDB

## What this project demonstrates

Enterprise RAG has two separate problems:

1. Find information relevant to the user's question.
2. Determine whether the user is allowed to receive that information.

These are not the same problem.

A retrieval system may correctly find a restricted policy because it is highly relevant to the question. That does not mean the user should be allowed to see it.

This project makes that separation explicit.

The core principle is:

> **Retrieval determines relevance.**  
> **Authorization determines access.**  
> **The language model generates the response.**

## Architecture


                    POLICY DOCUMENTS
                           |
                           v
                      INGESTION
                           |
                 +---------+---------+
                 |                   |
                 v                   v
             Chunking          Role metadata
                 |                   |
                 +---------+---------+
                           |
                           v
                      EMBEDDINGS
                           |
                           v
                       ChromaDB
                           |
                           v
                  Semantic retrieval
                           |
                           v
                 Role-based ACL
                    /         \
               allowed       blocked
                  |              |
                  v              X
          Authorized context
                  |
                  v
             Language model
                  |
                  v
                Answer


Authorization happens **after retrieval but before generation**.

Unauthorized chunks are removed before they are included in the model context.

The system therefore does not rely on the language model to decide what a user is allowed to see.

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
chunk minimum role level <= user role level
```

For example:

```text
Associate user
    |
    +-- Associate policy  -> ALLOW
    +-- Senior policy     -> BLOCK
    +-- Executive policy  -> BLOCK
```

The important security boundary is:

```text
Retrieve
   |
   v
Authorize
   |
   +---- Unauthorized content removed
   |
   v
Authorized context
   |
   v
Generate
```

The language model receives only the authorized context.

## Why section-level authorization matters

The policy documents contain multiple role sections within the same document.

For example:

```text
Associate section
Senior section
Executive section
```

A document-level permission is therefore too coarse.

If the entire document were treated as Executive-only, users could be prevented from accessing legitimate lower-level policy information.

If the entire document were treated as Associate-accessible, restricted Executive information could potentially become available.

The ingestion pipeline identifies role section headers and assigns the appropriate authorization metadata to each chunk.

This makes the authorization boundary match the actual policy content boundary.

## Local implementation

The repository contains the fully local implementation.

It uses:

* Ollama
* `nomic-embed-text`
* `llama3.2:3b`
* ChromaDB
* Python
* Streamlit

### Ollama

Ollama is the local runtime used to run the AI models.

It allows the application to perform model inference directly on the local machine without requiring a hosted LLM API for the core pipeline.

### `nomic-embed-text`

`nomic-embed-text` is the local embedding model.

It converts policy text and user questions into numerical vectors.

These vectors are used for semantic retrieval.

It does not generate the final answer.

### `llama3.2:3b`

`llama3.2:3b` is the local generation model.

After retrieval and authorization, it receives:

```text
User question
+
Authorized policy context
```

It then generates the final answer.

### ChromaDB

ChromaDB is the vector database used by the project.

It stores:

* Policy chunks
* Embeddings
* Authorization metadata

It performs semantic similarity retrieval against the stored policy embeddings.

## Hosted demonstration

The live Streamlit demonstration uses hosted inference because Streamlit Community Cloud does not provide the local Ollama runtime.

Its architecture is:

```text
User question
      |
      v
OpenAI embedding
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

The hosted demonstration uses OpenAI APIs for:

1. Creating embeddings for policy chunks and user questions.
2. Generating the final answer.

The application still controls retrieval and authorization.

The important distinction is:

```text
Fully local version
Ollama
  ├── nomic-embed-text
  └── llama3.2:3b
       +
    ChromaDB
       +
  Application ACL
```

versus:

```text
Hosted demonstration
OpenAI embeddings
       +
    ChromaDB
       +
  Application ACL
       +
OpenAI generation
```

The hosted demonstration is provided for convenience so that the project can be experienced without installing the local AI runtime.

## Evaluation

The local governance evaluation currently passes all 8 scenarios:

```text
8/8 passed
```

The tests cover both:

* Authorized retrieval
* Unauthorized retrieval

In denial scenarios, the target restricted chunk is explicitly verified to be blocked before generation.

The project also has a separate cloud MCP evaluation with:

```text
39/39 passed
```

These are separate evaluation suites and should not be treated as a direct benchmark comparison.

## Example behavior

### Authorized Associate access

An Associate asking for the Associate travel budget in the Americas can receive:

```text
$8,000 per year
```

### Restricted Associate access

An Associate asking for Executive compensation does not receive the Executive compensation information.

The restricted chunks are removed before generation.

### Authorized Executive access

An Executive asking for Executive compensation can receive:

```text
$180,000–$350,000 base annually,
plus bonus and equity per grade.
```

The same authorization logic is used for both allowed and restricted requests.

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

This reads the policy documents, identifies role sections, creates role-aware chunks, generates local embeddings, and stores the resulting data in ChromaDB.

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

### 8. Run the local Streamlit application

```bash
streamlit run app.py
```

The local implementation uses Ollama for embeddings and generation.

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
    ├── DunderMifflin_APAC_*.docx
    ├── DunderMifflin_Americas_*.docx
    └── DunderMifflin_Europe_*.docx
```

Generated runtime data such as the local virtual environment and ChromaDB storage are excluded from the repository.

## Performance

The local implementation was tested on an 8 GB Apple Silicon Mac.

Five repeated local runs produced:

```text
4.71s
1.59s
1.25s
1.55s
1.64s
```

Warm median:

```text
1.59 seconds
```

Generation is generally the largest contributor to end-to-end latency, while embedding and ChromaDB retrieval are comparatively fast.

## Context window observation

The installed `llama3.2:3b` model reported a maximum context length of 131,072 tokens.

The local Ollama runtime, however, showed a current context allocation of 4,096 tokens on the test machine.

This illustrates an important distinction between model capability and practical runtime configuration.

## Limitations

This is a portfolio-scale demonstration, not a production enterprise authorization platform.

A production implementation would additionally require considerations such as:

* Identity and authentication integration
* Centralized authorization policy management
* Audit logging
* Encryption
* Document versioning
* Policy lifecycle management
* Monitoring and alerting
* Larger evaluation suites
* Production-grade model serving
* Secret and key management
* Operational controls

The project intentionally focuses on demonstrating the architectural principle of enforcing authorization before sensitive context reaches the language model.

## Product lesson

The interesting part of this project is not the chatbot.

It is the architecture.

Enterprise RAG needs both retrieval and authorization.

Finding the right information is not enough. The system must also determine whether the current user is allowed to receive that information.

The language model should not be the security boundary.

The application should determine what context the model is allowed to receive.

A practical exploration of local AI, enterprise RAG, and governance-aware system design.
## Built by Ashutosh :)

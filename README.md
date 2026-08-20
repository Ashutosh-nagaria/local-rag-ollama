# Local Enterprise Policy RAG

A fully local RAG system for enterprise policy retrieval with role-based access control.

The system retrieves relevant policy content, applies authorization at the section and chunk level, and sends only authorized context to a local language model.

## Why this project exists

Enterprise RAG has two separate problems:

1. Find information relevant to the question.
2. Make sure the user is allowed to receive that information.

This project keeps those responsibilities separate.

> Retrieval determines relevance. Authorization determines access. The LLM generates the response.

## Architecture

```text
Policy Documents
       |
       v
    Ingestion
       |
       v
Section-level Role Metadata
       |
       v
   Embeddings
       |
       v
    ChromaDB
       |
       v
Semantic Retrieval
       |
       v
Role-based Authorization
       |
       +----------> Unauthorized content blocked
       |
       v
Authorized Context
       |
       v
     Ollama
       |
       v
  llama3.2:3b
       |
       v
     Answer
````

## Security model

Authorization happens after retrieval but before generation.

1. Retrieve potentially relevant policy chunks.
2. Read the minimum role required by each chunk.
3. Compare it with the user's role.
4. Remove unauthorized chunks.
5. Send only authorized context to the LLM.
6. Generate the answer.

The LLM is not responsible for deciding whether a user is authorized.

This matters because a single policy document can contain multiple privilege levels. Document-level permissions can therefore be too coarse.

This project assigns authorization metadata at the section and chunk level so that the security boundary follows the actual policy content.

## Role hierarchy

The demonstration uses three roles:

| Role      | Level |
| --------- | ----: |
| Associate |     1 |
| Senior    |     2 |
| Executive |     3 |

A chunk is authorized when:

```text
user role level >= chunk required role level
```

For example:

```text
Associate user + Associate content = Allowed
Associate user + Executive content = Blocked
Executive user + Associate content = Allowed
```

## Technology

| Technology       | Purpose                                                      |
| ---------------- | ------------------------------------------------------------ |
| Python           | Application, ingestion, retrieval, authorization, evaluation |
| Ollama           | Local model runtime                                          |
| llama3.2:3b      | Local answer generation                                      |
| nomic-embed-text | Local embeddings                                             |
| ChromaDB         | Local vector database                                        |
| Streamlit        | Local web interface                                          |
| python-docx      | DOCX document processing                                     |

## Evaluation

The local governance evaluation contains eight scenarios covering authorized and unauthorized retrieval.

**Result: 8/8 passed**

The denial scenarios verify that restricted chunks are blocked before they reach the language model.

## Performance

The application measures:

* Embedding time
* Retrieval time
* Generation time
* Total latency

Generation is generally the largest component of latency because the language model generates the response sequentially.

Actual performance depends on local hardware, model size, context configuration, corpus size, and runtime configuration.

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
```

The `docs/` directory contains the synthetic policy documents used by the demonstration.

Generated runtime artifacts such as `venv/` and `chroma_db/` are excluded from Git.

## Run locally

### Requirements

You will need:

* Python 3
* Git
* Ollama
* Sufficient local hardware to run the selected models

### Clone the repository

```bash
git clone https://github.com/Ashutosh-nagaria/local-rag-ollama.git
cd local-rag-ollama
```

You can also download the repository as a ZIP from GitHub.

### Install the Ollama models

Install Ollama, then run:

```bash
ollama pull llama3.2:3b
ollama pull nomic-embed-text
```

### Create a Python environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### Install dependencies

```bash
pip install -r requirements.txt
```

### Build the local policy index

```bash
python3 ingest.py
```

### Run the governance evaluation

```bash
python3 eval_local.py
```

Expected result:

```text
=== Results: 8/8 passed ===
```

### Run the command-line interface

```bash
python3 query.py
```

### Run the Streamlit interface

```bash
streamlit run app.py
```

The terminal will provide a local URL, normally:

```text
http://localhost:8501
```

## Documentation

See [CONCEPTS.md](CONCEPTS.md) for detailed explanations of:

* RAG
* Embeddings
* Vector retrieval
* Chunking
* Section-level authorization
* Role hierarchies
* Ollama
* Context length
* Ingestion
* Query processing
* Evaluation
* Local deployment trade-offs
* Production considerations

## Data and privacy

The repository contains synthetic demonstration policy documents.

The core inference pipeline is designed to run locally.

Do not replace the demonstration corpus with confidential enterprise information unless the environment is appropriately secured and controlled.

## Production considerations

This repository demonstrates the architecture at portfolio scale.

A production implementation would additionally require:

* Trusted enterprise identity
* Identity provider integration
* Centralized authorization policy management
* Audit logging
* Encryption
* Document versioning
* Policy lifecycle management
* Monitoring and observability
* Security testing
* Prompt injection testing
* Data leakage testing
* Production-grade model serving

The role selector in the Streamlit application is a demonstration of authorization logic. It is not a production authentication mechanism.

## License

No open-source license is currently specified. The repository is published as a technical portfolio demonstration.

## Built by

**Ashutosh Nagaria**

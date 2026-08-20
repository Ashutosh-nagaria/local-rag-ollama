# Local Enterprise Policy RAG

A fully local, governance-aware RAG system for enterprise policy questions.

It uses Ollama, llama3.2:3b, nomic-embed-text, ChromaDB, Python, and Streamlit. Policy content stays on the local machine.

## Why this project exists

A normal RAG system can retrieve relevant information but still create a security problem if the retrieved information belongs to a higher-privilege user.

This project treats authorization as part of the retrieval pipeline. Unauthorized policy chunks are removed before they reach the LLM.

## Architecture

Policy documents -> ingestion -> role tagging -> embeddings -> ChromaDB -> semantic retrieval -> role-based authorization -> authorized context -> local LLM -> answer.

## Key security idea

Authorization happens after retrieval but before generation.

1. Retrieve potentially relevant policy chunks.
2. Read the minimum role required by each chunk.
3. Compare it with the user role.
4. Remove unauthorized chunks.
5. Send only authorized context to the LLM.
6. Generate the answer.

The system does not rely on the LLM to decide what the user is allowed to see. Sensitive information is removed before the LLM receives it.

## ELI5

Imagine three filing cabinets: Associate, Senior, and Executive.

An employee asks for Executive compensation information. The search system may find the Executive document, but a security guard checks the employee role before allowing the document through.

If the employee is not authorized, the document is blocked and never reaches the AI.

## The governance bug we found

The source DOCX files contained document-level Min-Role metadata, but a single document could contain Associate, Senior, and Executive sections.

A document-level permission was therefore too coarse.

The ingestion pipeline was rebuilt to detect role section headers and assign role metadata to each chunk. This makes the authorization boundary match the actual policy content boundary.

## Role hierarchy

Associate = 1
Senior = 2
Executive = 3

A chunk is authorized when its minimum required role level is less than or equal to the user's role level.

## Models

### nomic-embed-text

The local embedding model. It converts policy text and user questions into numerical representations so semantically similar content can be retrieved.

It does not generate the final answer.

### llama3.2:3b

The local generation model. It receives the question and authorized policy context and generates the final answer.

### Ollama

The local model runtime that runs both models without requiring a hosted LLM API for the core pipeline.

## ChromaDB

ChromaDB is the local vector database. It stores policy chunks, embeddings, and metadata such as source, zone, minimum role, and minimum role level.

## Evaluation

The local governance evaluation currently passes all 8 scenarios.

Result:

8/8 passed

The tests cover both authorized retrieval and unauthorized retrieval. In denial cases, the target restricted chunk is explicitly verified to be blocked before the LLM.

The earlier cloud MCP implementation has a separate evaluation suite with 39/39 tests passing. These are separate suites and should not be treated as a direct benchmark comparison.

## Example

An Associate asking for the Associate compensation band in the Americas receives:

5,000 - 5,000 base annually.

An Executive asking for the Executive compensation band in the Americas can receive:

80,000 - 50,000 base annually, plus bonus and equity per grade.

An Associate asking for the Executive compensation band has the Executive chunk blocked before it reaches the LLM.

## Performance

Five repeated local runs produced:

4.71s
1.59s
1.25s
1.55s
1.64s

Warm median: 1.59 seconds.

Generation is generally the largest contributor to latency. Embedding and ChromaDB retrieval are comparatively fast.

## Context window finding

The installed llama3.2:3b model reports a maximum context length of 131,072 tokens.

However, ollama ps showed a current runtime context allocation of 4,096 tokens on this machine.

This demonstrates an important local AI distinction: model capability and practical runtime configuration are not always the same thing.

## Cloud versus local

| Dimension | Cloud MCP | Local RAG |
|---|---|---|
| Data location | Cloud/server | Local machine |
| Generation | Hosted model | Ollama |
| Retrieval | Policy lookup | Vector retrieval |
| Embeddings | Service dependent | Local |
| Vector store | Cloud architecture | ChromaDB |
| Authorization | Before policy response | Before LLM context |
| External API dependency | Yes | No for core inference |
| Main trade-off | Managed infrastructure | Local hardware constraints |

Local is not universally better. It provides stronger control over data location and external dependencies, while requiring local hardware and model serving.

## Project structure

local-rag-ollama/
- app.py
- ingest.py
- query.py
- eval_local.py
- requirements.txt
- README.md
- CONCEPTS.md
- .gitignore
- docs/

chroma_db and venv are generated locally and excluded from Git.

## Setup

### Pull models

ollama pull llama3.2:3b
ollama pull nomic-embed-text

### Install dependencies

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

### Ingest policies

python3 ingest.py

### Run CLI

python3 query.py

### Run governance evaluation

python3 eval_local.py

Expected result:

8/8 passed

### Run Streamlit

streamlit run app.py

## Limitations

This is a portfolio-scale demonstration, not a production enterprise authorization platform.

Production deployment would additionally require identity integration, centralized authentication, stronger authorization policy management, audit logging, encryption, document versioning, monitoring, larger evaluation suites, and production-grade model serving.

## Product lesson

The interesting part of this project is not the chatbot. It is the architecture.

Authorization is enforced as a deterministic system-level control before sensitive information reaches the model.

This demonstrates how enterprise RAG can combine semantic retrieval with explicit governance rather than relying on prompting alone.

## Interview summary

I built a fully local, governance-aware RAG system to explore what changes when enterprise policy retrieval moves from cloud infrastructure to an on-prem style architecture.

I used local embeddings, ChromaDB, Ollama, and a small Llama model.

The key design decision was enforcing role-based authorization before retrieved policy chunks reached the LLM.

I found and fixed a real bug where document-level permissions could expose restricted sections, so I moved authorization metadata to the section and chunk level.

The final local system passed 8 out of 8 governance scenarios and achieved a 1.59 second warm median latency on an 8 GB Apple Silicon Mac.

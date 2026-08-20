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

> **Retrieval determines relevance.  
> Authorization determines access.  
> The language model generates the response.**

## Architecture

```text
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

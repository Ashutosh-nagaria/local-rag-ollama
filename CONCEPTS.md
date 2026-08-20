# Concepts: Local Enterprise Policy RAG

## 1. What problem are we solving?

This project is a private AI assistant for company policies.

Employees can ask questions such as:

- What is my travel budget?
- How much parental leave do I receive?
- What is my compensation band?
- What approval process applies to my role?

The challenge is that finding information is not enough.

The system must also determine whether the employee is allowed to receive that information.

The core product problem is therefore:

Find the right information, while preventing users from receiving information they are not authorized to see.

## 2. What is RAG?

RAG means Retrieval-Augmented Generation.

In simple terms, instead of asking an AI model to answer only from its training knowledge, we first search our own company documents and give the relevant information to the model.

Think of an open-book exam.

Without RAG, the student answers from memory.

With RAG, the student receives the relevant pages of the company policy manual before answering.

The basic flow is:

Question -> Retrieve relevant information -> Give context to LLM -> Generate answer

## 3. Why not give every document to the LLM?

There are two problems.

First, there may be too much information.

Second, some information may be restricted.

An Associate should not automatically receive Executive compensation information simply because the search system found it.

Therefore we need both retrieval and authorization.

## 4. What is an embedding?

An embedding is a numerical representation of the meaning of text.

For example, these questions have different words but similar meaning:

How much can I spend on business travel?

What is my annual travel budget?

An embedding model converts both into numerical vectors. Similar meanings produce vectors that are closer together.

The simple mental model is:

Embedding = meaning represented as numbers.

## 5. What is nomic-embed-text?

nomic-embed-text is the embedding model used in this project.

Its job is not to answer questions.

Its job is to convert text into vectors.

During ingestion:

Policy text -> nomic-embed-text -> vector

During a query:

User question -> nomic-embed-text -> question vector

The system then compares the question vector with stored policy vectors to find relevant chunks.

The model runs locally through Ollama.

## 6. What is a vector database?

Once text has been converted into vectors, we need somewhere to store them.

That is the role of a vector database.

A traditional database can answer questions such as:

Find documents where country equals Americas.

A vector database can answer:

Find information whose meaning is similar to this question.

That is why vector databases are useful for RAG.

## 7. Why ChromaDB?

ChromaDB is the local vector database used by this project.

It stores:

- Policy chunks
- Embeddings
- Source information
- Geographic zone
- Minimum required role
- Minimum role level

The database runs locally.

This means the demonstration does not need a cloud vector database.

## 8. What is chunking?

A large policy document is not stored as one giant block.

It is split into smaller pieces called chunks.

The project uses a target chunk size of approximately 500 characters.

The reason is simple.

If a 20-page policy is stored as one giant object, a question about travel reimbursement could retrieve the entire policy.

Smaller chunks allow the system to retrieve more focused information.

There is a trade-off.

Chunks that are too small can lose context.

Chunks that are too large can reduce retrieval precision.

The 500-character value is therefore a practical portfolio choice, not a universal optimum.

## 9. The important governance bug

This was one of the most valuable discoveries in the project.

The source policy documents contained document-level minimum-role metadata.

For example:

Min-Role = Associate

The problem was that one document could contain multiple role sections:

Associate
Senior
Executive

A document-level permission was therefore too coarse.

An Associate-labelled document could contain an Executive-only section.

That creates a potential security leak.

The problem was not the LLM.

The problem was authorization granularity.

## 10. How we fixed the bug

The ingestion pipeline was changed so that role information is detected at the section level.

Each section gets its own required role.

Each chunk then inherits the role of the section it came from.

Conceptually:

Associate section -> Associate chunks

Senior section -> Senior chunks

Executive section -> Executive chunks

This makes the authorization boundary match the actual content boundary.

That is much safer than treating the entire document as having one permission level.

## 11. Role hierarchy

The project uses three roles:

Associate = 1

Senior = 2

Executive = 3

The authorization rule is:

User role level >= required role level

Examples:

Associate user = 1
Associate content = 1
1 >= 1
Allowed.

Associate user = 1
Executive content = 3
1 >= 3
Blocked.

Executive user = 3
Associate content = 1
3 >= 1
Allowed.

This is a simple role-based access-control model.

## 12. Why authorization happens before the LLM

This is the most important architectural decision.

A weak design would be:

Retrieve everything -> Give everything to LLM -> Tell LLM not to reveal restricted information.

That is risky because the LLM has already received the sensitive information.

This project instead does:

Retrieve candidates -> Authorization filter -> Remove unauthorized chunks -> Build authorized context -> LLM

The blocked information never reaches the generation model.

This makes the authorization boundary deterministic and easier to test.

## 13. ELI5 security analogy

Imagine a library.

The search system is the librarian.

The LLM is the reader.

The librarian finds five books that might answer the question.

The employee's access badge says they can only read three.

The librarian removes the two restricted books before giving the books to the reader.

The reader never sees the restricted books.

That is what the authorization filter does.

## 14. What is Ollama?

Ollama is the local runtime used to run the AI models.

Instead of sending model requests to a hosted API, the application communicates with Ollama running on the local computer.

Cloud:

Application -> Internet -> Hosted LLM

Local:

Application -> Ollama -> Local model

This is useful when privacy, offline operation, or on-prem deployment is important.

## 15. What is llama3.2:3b?

llama3.2:3b is the generation model used in this project.

The 3B means approximately three billion parameters.

It is intentionally small enough to run on the local machine used for this demonstration.

The trade-off is:

Smaller local model means lower hardware requirements and local privacy, but generally weaker reasoning and generation quality than larger models.

The project is not claiming the small local model is universally better.

It demonstrates a different deployment choice.

## 16. What is context length?

Context length is approximately how much text the model can consider in one interaction.

The installed llama3.2:3b model reports a maximum context length of 131,072 tokens.

However, ollama ps showed a current runtime context allocation of 4,096 tokens on this machine.

This distinction matters.

Maximum model capability does not automatically mean that the local computer will practically run the model at that context size.

Larger context generally requires more memory.

## 17. What does ollama ps do?

The command:

ollama ps

shows models currently loaded by Ollama.

It can show:

- Model name
- Model identifier
- Memory usage
- Processor usage
- Context allocation
- How long the model will remain loaded

In our testing, llama3.2:3b and nomic-embed-text were running on the GPU.

## 18. What happens during ingestion?

The ingestion pipeline prepares the policy corpus.

The simplified flow is:

DOCX files -> Read text -> Identify roles and regions -> Detect role sections -> Split into chunks -> Create embeddings -> Store chunks, embeddings, and authorization metadata -> ChromaDB

The result is a searchable local policy index.

## 19. What happens during a query?

The query pipeline is:

User role + question

-> Embed question

-> Search ChromaDB

-> Retrieve candidate chunks

-> Apply role authorization

-> Remove unauthorized chunks

-> Build authorized context

-> Send context to llama3.2:3b

-> Generate answer

Retrieval and authorization are separate operations.

Retrieval asks:

What information looks relevant?

Authorization asks:

Is this user allowed to receive it?

Those are different questions.

## 20. Why can retrieval return unauthorized information?

Semantic similarity does not understand business permissions.

Suppose an Associate asks:

What is the compensation band?

The search system may find:

- Associate compensation
- Senior compensation
- Executive compensation

All three can be semantically relevant.

The vector database is doing its job.

It is finding similar information.

It is not responsible for deciding whether the user is authorized.

That is why authorization happens after retrieval.

## 21. Evaluation

The local project has eight governance test cases.

Current result:

8/8 passed

The tests cover both positive and negative authorization scenarios.

Positive tests verify that authorized target chunks are allowed.

Negative tests verify that restricted target chunks are blocked before reaching the LLM.

Examples include:

L04 | Associate | target chunk blocked before LLM

L05 | Senior | target chunk blocked before LLM

L06 | Associate | target chunk blocked before LLM

This is stronger than simply checking whether the final answer looks safe.

The evaluation checks the actual security boundary.

## 22. Performance

The application measures:

Embedding time
Retrieval time
Generation time
Total time

Example:

Embedding: 0.08 seconds

Retrieval: 0.01 seconds

Generation: 1.43 seconds

Total: 1.55 seconds

Generation is normally the largest component because the LLM generates the answer token by token.

Local vector retrieval is comparatively fast for this corpus.

## 23. Why local can be attractive

A local architecture can provide:

- Strong control over data location
- No hosted LLM API required for core inference
- No cloud inference charge for local generation
- Offline operation
- Local model control
- A path toward on-prem deployment

But these benefits come with operational trade-offs.

## 24. Local trade-offs

Local AI also means owning the infrastructure.

Potential disadvantages include:

- Hardware limitations
- Memory constraints
- Slower inference for larger models
- Model management
- Updates and maintenance
- Smaller models may produce weaker answers
- More operational responsibility

Therefore:

Local is not automatically better.

Cloud is not automatically better.

The correct architecture depends on product requirements.

## 25. Cloud versus local product decision

Cloud infrastructure can be attractive when a team wants managed infrastructure, easier scaling, and access to powerful hosted models.

Local infrastructure can be attractive when data control, privacy, offline operation, or on-prem requirements are more important.

A PM should ask:

- What data can leave the environment?
- What latency is acceptable?
- What model quality is required?
- What hardware exists?
- What compliance requirements exist?
- What operating cost is acceptable?
- How much infrastructure can the team operate?

These requirements should drive the architecture.

## 26. What would production require?

This project is a portfolio-scale demonstration.

A production implementation would need additional controls such as:

- Enterprise authentication
- Identity provider integration
- Central authorization policy management
- Audit logging
- Encryption
- Document versioning
- Policy lifecycle management
- Monitoring
- Security testing
- Production-grade model serving

The simple role selection used in this demonstration would be replaced by a trusted identity and authorization system.

## 27. What would I improve next?

If this became a real product, I would prioritize:

1. Real enterprise identity integration.
2. Centralized authorization policies.
3. Audit logs for retrieval and authorization decisions.
4. Better document versioning.
5. More comprehensive evaluation.
6. Stronger models where hardware permits.
7. Retrieval quality evaluation separate from generation quality.
8. Security testing for prompt injection and indirect data leakage.
9. Production observability.
10. A larger benchmark comparing local and cloud quality, latency, cost, and privacy.

## 28. What is actually interesting about the project?

The individual technologies are not novel.

RAG exists.

Ollama exists.

ChromaDB exists.

Role-based access control exists.

The interesting product and engineering insight is how they are combined.

The project demonstrates:

Semantic retrieval
+
Explicit authorization
+
Local inference
+
Measured performance

The key lesson is that enterprise AI governance should be implemented as a system-level control, not just as a prompt instruction.

## 29. How to explain it to a non-technical person

I built a private AI assistant for company policies.

It searches company documents and answers questions locally.

Before giving information to the AI, it checks the employee's role.

So an Associate can receive Associate information, while Executive-only information is filtered out before the AI ever sees it.

## 30. How to explain it to a technical person

I built a local RAG pipeline using section-level role metadata, ChromaDB for vector retrieval, nomic-embed-text for embeddings, and llama3.2:3b through Ollama for generation.

The retrieval stage returns candidates.

A role-level authorization filter then removes unauthorized chunks before the authorized context is passed to the LLM.

## 31. How to explain it to an Engineering Manager

The key architectural decision was separating semantic retrieval from authorization.

Retrieval determines relevance.

An explicit ACL layer determines whether a retrieved chunk can enter the generation context.

We discovered that document-level scope was too coarse because documents contained multiple role sections.

We therefore moved authorization metadata to the section and chunk level.

We then validated the security boundary with eight automated authorization scenarios, all of which passed.

## 32. How to explain it as a PM

The strongest PM story is not:

I built a chatbot.

The stronger story is:

I identified a governance problem in enterprise RAG, reproduced the architecture in a fully local environment, found a real authorization granularity bug, redesigned the permission boundary at the content level, and measured the resulting system across authorization correctness and local performance.

That demonstrates:

- Problem framing
- Risk identification
- Architecture decisions
- Trade-off analysis
- Iterative debugging
- Evaluation
- Product thinking

## 33. Final mental model

Remember three questions.

RAG asks:

What information is relevant?

Authorization asks:

What information is this user allowed to receive?

The LLM asks:

How should I explain the authorized information?

Those responsibilities should not be confused.

The core architecture is:

Question
|
v
Relevance
|
v
Authorization
|
v
Generation
|
v
Answer

That separation is the central design principle of this project.

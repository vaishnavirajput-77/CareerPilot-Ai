# Architecture

```mermaid
flowchart TD
  A[Next.js dashboard] -->|REST / JSON| B[FastAPI]
  B --> C[Resume parser]
  B --> D[ML matching service]
  B --> E[Skill gap and roadmap service]
  B --> F[Interview practice service]
  B --> G[(PostgreSQL / SQLite dev)]
  D --> H[TF-IDF + cosine similarity]
  C --> I[PDF text extraction + skill taxonomy]
```

The current starter uses transparent, lightweight algorithms. LLM calls are not required for the core ML flow. Before production, add authenticated user identity, per-user row ownership, migrations, private object storage, rate limits, and monitored deployment.

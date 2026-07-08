# Narrative Engine Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         NARRATIVE ENGINE                                │
│                    Qualitative Historical Forecasting                     │
└─────────────────────────────────────────────────────────────────────────┘

┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   INGESTION  │───▶│  EXTRACTION  │───▶│   STORAGE    │───▶│  RETRIEVAL   │
│              │    │              │    │              │    │              │
│ • Books      │    │ • Segment    │    │ • PostgreSQL │    │ • Vector     │
│ • Articles   │    │ • Extract    │    │ • pgvector │    │   Search     │
│ • Archives   │    │ • Classify   │    │ • SQLAlchemy│    │ • Graph      │
│ • PDFs       │    │ • Link       │    │ • Alembic   │    │   Traversal  │
└──────────────┘    └──────────────┘    └──────────────┘    └──────┬───────┘
                                                                    │
┌──────────────┐    ┌──────────────┐    ┌──────────────┐           │
│  EVALUATION  │◀───│   THESIS     │◀───│   GENERATE   │◀──────────┘
│              │    │              │    │              │
│ • Brier      │    │ • Forecast   │    │ • Synthesize │
│   Score      │    │ • Confidence │    │ • Cluster    │
│ • Calibration│    │ • Watch      │    │ • Weight     │
│ • Backtest   │    │   Conditions │    │ • Rank       │
└──────────────┘    └──────────────┘    └──────────────┘
```

## Data Flow

### Phase 1: Ingestion
**Input:** Raw historical texts (Kindleberger, Taleb, archives)
**Output:** Chunks with metadata

```
[Source Documents]
       │
       ▼
[Text Chunking] ──▶ [Metadata: source, date, author]
       │
       ▼
[Chunks Queue]
```

### Phase 2: Extraction
**Input:** Text chunks
**Output:** Structured Episodes

```
[Chunk]
   │
   ├──▶ [Segmentation] ──▶ Episode boundaries
   │
   ├──▶ [Extraction] ───▶ Actors, conditions, mechanics
   │
   ├──▶ [Classification] ──▶ Arc type + phase
   │
   └──▶ [Linking] ──────▶ Causal connections
   │
   ▼
[Episode] ──▶ Database
```

### Phase 3: Storage
**Data Model:**

```
┌─────────────────────────────────────────────┐
│                   EPISODE                     │
├─────────────────────────────────────────────┤
│ id (UUID)                                   │
│ title, summary                              │
│ arc_type (enum) ──┐                         │
│ arc_phase (enum) ─┼──▶ Arc classification  │
│ actors[]          │                         │
│ initiating_conditions[]                     │
│ escalation_mechanics[]                     │
│ tension                                     │
│ resolution                                  │
│ consequences[]                              │
│ embedding (vector) ───▶ pgvector          │
└─────────────────────────────────────────────┘
         │
         │ many-to-many
         ▼
┌─────────────────────────────────────────────┐
│                   CYCLE                     │
├─────────────────────────────────────────────┤
│ Fractal containment:                        │
│ • Civilizational (~centuries)               │
│ • Institutional (~decades)                  │
│ • Generational (~25 years)                │
│ • Episodic (individual)                   │
└─────────────────────────────────────────────┘
```

### Phase 4: Retrieval
**Analog Retrieval:**

```
[Query Episode]
      │
      ├──▶ [Embedding] ──▶ Vector (384-dim)
      │
      ├──▶ [Vector Search] ──▶ Candidates (pgvector)
      │
      ├──▶ [Score] ──▶ Combined score:
      │       • Semantic: 50%
      │       • Arc match: 20%
      │       • Phase compat: 15%
      │       • Cycle context: 15%
      │
      ▼
[Top K Analogs] ──▶ Ranked by relevance
```

### Phase 5: Generation
**Thesis Synthesis:**

```
[Query + Analogs]
      │
      ├──▶ [Filter] ──▶ Quality threshold (≥0.6)
      │
      ├──▶ [Extract] ──▶ "What happened next?"
      │
      ├──▶ [Cluster] ──▶ Group similar outcomes
      │
      ├──▶ [Weight] ──▶ By analog relevance
      │
      └──▶ [Generate] ──▶ 2-3 continuations
      │
      ▼
[Thesis]
   • Dominant continuation (highest prob)
   • Alternative continuations
   • Confidence level
   • Watch conditions
   • Key uncertainties
```

### Phase 6: Evaluation
**Metrics:**

```
[Thesis + Actual Outcome]
          │
          ├──▶ [Brier Score] = (prob - outcome)²
          │
          ├──▶ [Calibration] ──▶ ECE per bin
          │
          ├──▶ [Accuracy] ──▶ matched / total
          │
          └──▶ [Lessons] ──▶ Missed factors
```

## Key Design Decisions

### 1. Fractal Time
Cycles nest: civilizational ⊃ institutional ⊃ generational ⊃ episodic

### 2. Probabilistic Forecasts
Not point predictions — distributions weighted by analog confidence

### 3. Epistemic Humility
"Unknown" confidence when insufficient analogs

### 4. Transparency
Each continuation cites supporting evidence count

### 5. Actionable
Watch conditions extracted from escalation mechanics

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.10+ |
| Database | PostgreSQL 16 + pgvector |
| ORM | SQLAlchemy 2.0 (async) |
| Embeddings | sentence-transformers |
| LLM | OpenAI / Anthropic |
| Testing | pytest + asyncpg |
| CI/CD | GitHub Actions |
| Container | Docker + Docker Compose |

## Performance Considerations

- **Embeddings:** Cached in Redis (production)
- **Vector Search:** IVFFlat index on pgvector
- **LLM Calls:** Retried with exponential backoff
- **Database:** Async connection pooling

## Security

- API keys via environment variables
- Database credentials isolated
- No secrets in repository
- Token-based auth for LLM providers

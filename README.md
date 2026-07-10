# Narrative Engine

A system for qualitative historical forecasting through narrative arc extraction.

## Overview

The Narrative Engine treats history as a corpus of stories with recurring arcs. It uses LLMs to extract, classify, and structure those arcs at multiple time scales, then generates forecasts ("theses") by asking: **"Given where we are in the story, how do stories like this usually end?"**

## Core Concepts

- **Episode**: Atomic narrative unit (e.g., "Weimar hyperinflation, 1921–1923")
- **Arc**: Archetypal shape (e.g., "credit boom and bust", "hubris–nemesis")
- **Cycle**: Fractal containers (civilizational → institutional → generational)
- **Thesis**: Generated forecast with historical analogs and confidence intervals

## Architecture

```
src/narrative_engine/
├── ingestion/        # Text ingestion from books, articles, archives
├── extraction/       # LLM pipeline: segmentation, classification, linking
├── storage/          # Database: SQLAlchemy models, pgvector, repositories
├── retrieval/        # Analog retrieval: semantic search, graph traversal
├── generation/       # Thesis synthesis from historical analogs
└── evaluation/       # Backtesting, calibration, Brier scores
```

## Quick Start

### Installation

```bash
pip install -e ".[dev]"
```

### Database Setup

```bash
# Create PostgreSQL database with pgvector
createdb narrative_engine

# Run migrations
alembic upgrade head
```

### Running Tests

```bash
pytest -v
```

### Example Usage

```python
from narrative_engine.models import Episode, ArcType, ArcPhase
from narrative_engine.storage.database import db_manager
from narrative_engine.storage.repositories import RepositoryFactory

async with db_manager.session() as session:
    factory = RepositoryFactory(session)
    
    # Create episode
    episode = await factory.episodes.create(
        Episode(
            title="1929 Stock Market Crash",
            summary="The collapse of the US stock market in October 1929",
            arc_type=ArcType.CREDIT_BOOM_AND_BUST,
            arc_phase=ArcPhase.PANIC,
        )
    )
    
    # Retrieve by arc type
    similar = await factory.episodes.get_by_arc_type(
        ArcType.CREDIT_BOOM_AND_BUST.value
    )
```

## How To Use

### Data Ingestion

The Narrative Engine processes historical texts to extract structured narrative episodes. Here's how to add your own data:

#### Supported Data Types

| Type | Format | Examples |
|------|--------|----------|
| **Books** | PDF, EPUB, TXT | Kindleberger's *Manias, Panics, and Crashes*, Taleb's *The Black Swan* |
| **Articles** | TXT, Markdown | Academic papers, journalism, historical essays |
| **Archives** | JSON, CSV | Structured datasets like Reinhart-Rogoff crisis database |
| **Timelines** | JSON | Encyclopedic chronologies for scaffolding |

#### Ingestion Process

1. **Place raw files** in the `data/raw/` directory:
   ```
   data/raw/
   ├── books/kindleberger-mania-2026.pdf
   ├── articles/taleb-black-swan.txt
   └── archives/reinhart-rogoff-crisis.json
   ```

2. **Run the ingestion pipeline**:
   ```bash
   python -m narrative_engine.ingestion \
     --source-dir data/raw/ \
     --output-dir data/processed/
   ```

3. **Processed output** will be:
   - Text chunks (~2-8k tokens, respecting chapter boundaries)
   - Metadata (author, publication date, historiographic school)
   - Chunk IDs for provenance tracking

### Extraction Pipeline

After ingestion, run the LLM extraction pipeline:

```python
from narrative_engine.extraction.pipeline import ExtractionOrchestrator

orchestrator = ExtractionOrchestrator()

# Process a single chunk
episodes = await orchestrator.process_text(
    text="The stock market crash of 1929...",
    source_id="kindleberger-1929",
)

# Process entire directory
results = await orchestrator.process_directory("data/processed/")
```

**Pipeline stages**:
1. **Segmentation** → Episode boundaries + one-line summaries
2. **Extraction** → Actors, conditions, mechanics, resolution, consequences
3. **Classification** → Arc type + phase + confidence
4. **Linking** → Causal connections, cycle membership

### Expected Output

For each processed episode, you'll get:

```python
Episode(
    title="1929 Stock Market Crash",
    summary="The collapse of the US stock market in October 1929",
    arc_type=ArcType.CREDIT_BOOM_AND_BUST,
    arc_phase=ArcPhase.PANIC,
    actors=[
        Actor(name="Herbert Hoover", role="President"),
        Actor(name="J.P. Morgan Jr.", role="Banker"),
    ],
    initiating_conditions=[
        "Speculative excess",
        "Margin trading widespread",
    ],
    escalation_mechanics=[
        "Panic selling cascades",
        "Margin calls force liquidation",
    ],
    resolution="Market bottomed in 1932, down 89% from peak",
    consequences=[
        "Great Depression begins",
        "Banking crisis follows",
        "New Deal reforms enacted",
    ],
    embedding=[0.23, -0.15, 0.88, ...],  # 384-dim vector
)
```

### Generating Forecasts

Once episodes are extracted, generate forecasts ("theses"):

```python
from narrative_engine.retrieval.embeddings import EmbeddingGenerator
from narrative_engine.retrieval.analog_retrieval import AnalogRetriever
from narrative_engine.thesis.generator import ThesisGenerator

# Embed your current situation
query = Episode(
    title="2024 Market Conditions",
    summary="High valuations, AI bubble concerns, rising rates",
    arc_type=ArcType.CREDIT_BOOM_AND_BUST,
    arc_phase=ArcPhase.DISTRESS,
)

embedder = EmbeddingGenerator()
retriever = AnalogRetriever()
generator = ThesisGenerator()

# Retrieve historical analogs
query_embedding = embedder.generate_for_episode(query)
analogs = await retriever.find_analogs(query_embedding, query)

# Generate thesis
thesis = generator.generate(query, analogs)

print(f"Dominant continuation: {thesis.dominant_continuation}")
print(f"Confidence: {thesis.confidence}")
print(f"Watch conditions: {thesis.watch_conditions}")
```

**Example output**:

```
Dominant continuation: Soft landing likely (65% probability)
Confidence: 0.72
Watch conditions:
  - Credit spreads widening
  - Yield curve inversion persistence
  - Fed policy shift signals

Based on 12 historical analogs:
  - 1929 Crash (phase match: 0.85)
  - 2008 Financial Crisis (phase match: 0.78)
  - 1987 Black Monday (phase match: 0.72)
```

### Evaluation & Backtesting

Track forecast accuracy over time:

```python
from narrative_engine.evaluation.backtest import BacktestEngine
from narrative_engine.evaluation.metrics import BrierScore

# Run backtest on historical events
engine = BacktestEngine()
results = await engine.backtest(
    start_date="2000-01-01",
    end_date="2020-01-01",
)

# Score predictions
for thesis in results:
    score = BrierScore.calculate(
        probability=thesis.dominant_continuation.probability,
        outcome=thesis.resolved_outcome,
    )
    print(f"Brier score: {score.score}")  # Lower is better (0=perfect, 1=worst)
```

## Development

### Project Structure

- **Phase 1** ✅: Core models (Episode, Arc, Cycle, Thesis)
- **Phase 2** ✅: Database layer (SQLAlchemy, pgvector, ORM)
- **Phase 3** ✅: Repository pattern (CRUD, semantic search)
- **Phase 4** ✅: LLM extraction pipeline
- **Phase 5** ✅: Analog retrieval and thesis generation
- **Phase 6** ✅: Evaluation and backtesting

### PR History

| PR | Description | Status |
|----|-------------|--------|
| #2-#7 | Core → Database → Repository → Extraction | ✅ Merged |
| #8 | Vector Embeddings + Analog Retrieval | ✅ Merged |
| #9 | Thesis Generation | ✅ Merged |
| #10 | Testing + Documentation | ✅ Merged |
| #11 | Missing models fix | ✅ Merged |

## Design Principles

1. **Fractal time**: Cycles nest (civilizational → institutional → generational)
2. **Narrative arcs**: Episodes instantiate archetypal patterns
3. **Phase completion**: Forecasting by locating current position in arc
4. **Provenance**: Every claim traceable to source passages
5. **Evaluation**: Rigorous backtesting with Brier score calibration

## Related Documentation

- [Narrative Finance: Qualitative Forecasting](https://github.com/shewstone/NarrativeGenerator/wiki/Narrative-Finance-Qualitative-Forecasting)
- [Narrative Engine Technical Design](https://github.com/shewstone/NarrativeGenerator/wiki/Narrative-Engine-Technical-Design)
- [Fractal Time Framework](https://github.com/shewstone/NarrativeGenerator/wiki/fractal-time)

## License

MIT

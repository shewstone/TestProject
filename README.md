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

## Development

### Project Structure

- **Phase 1** ✅: Core models (Episode, Arc, Cycle, Thesis)
- **Phase 2** ✅: Database layer (SQLAlchemy, pgvector, ORM)
- **Phase 3** ✅: Repository pattern (CRUD, semantic search)
- **Phase 4** 🔄: LLM extraction pipeline
- **Phase 5**: Analog retrieval and thesis generation
- **Phase 6**: Evaluation and backtesting

### PR History

| PR | Description | Status |
|----|-------------|--------|
| #2 | Initial project structure and core models | ✅ Merged |
| #3 | Database layer with SQLAlchemy and pgvector | ✅ Merged |
| #4 | Repository pattern with CRUD operations | ✅ Merged |
| #5 | Alembic migrations and CI/CD | 🔄 Open |

## Design Principles

1. **Fractal time**: Cycles nest (civilizational → institutional → generational)
2. **Narrative arcs**: Episodes instantiate archetypal patterns
3. **Phase completion**: Forecasting by locating current position in arc
4. **Provenance**: Every claim traceable to source passages
5. **Evaluation**: Rigorous backtesting with Brier score calibration

## Related Documentation

- [Narrative Finance: Qualitative Forecasting](https://github.com/shewstone/TestProject/wiki/Narrative-Finance-Qualitative-Forecasting)
- [Narrative Engine Technical Design](https://github.com/shewstone/TestProject/wiki/Narrative-Engine-Technical-Design)
- [Fractal Time Framework](https://github.com/shewstone/TestProject/wiki/fractal-time)

## License

MIT

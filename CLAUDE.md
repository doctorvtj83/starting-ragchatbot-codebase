# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Running the Application
```bash
# Quick start (recommended)
./run.sh

# Manual start
cd backend && uv run uvicorn app:app --reload --port 8000
```

### Package Management
```bash
# Install dependencies
uv sync

# Add new dependency
uv add package_name
```

### Code Quality & Formatting
```bash
# Format code with black
./scripts/format.sh
uv run black .

# Check code formatting without changes
./scripts/check-format.sh
uv run black --check --diff .

# Run comprehensive quality checks
./scripts/quality-check.sh
```

### Environment Setup
- Create `.env` file with `ANTHROPIC_API_KEY=your_key_here`
- Application runs on http://localhost:8000
- API documentation available at http://localhost:8000/docs

## Architecture Overview

This is a full-stack RAG (Retrieval-Augmented Generation) system with a clear separation between frontend, backend, and data processing layers.

### Core Processing Flow
1. **Document Ingestion**: Files in `docs/` → DocumentProcessor → Text chunking → Vector storage
2. **Query Processing**: Frontend → FastAPI → RAG System → AI Generator → Anthropic Claude
3. **Search & Retrieval**: Claude uses CourseSearchTool → Vector search → ChromaDB → Formatted results
4. **Response Generation**: Claude synthesizes search results → Session management → Frontend display

### Key Components

**Backend Core (`backend/`)**:
- `app.py`: FastAPI application with CORS, static file serving, and API endpoints
- `rag_system.py`: Main orchestrator coordinating all components
- `ai_generator.py`: Anthropic Claude API integration with tool execution
- `config.py`: Centralized configuration with environment variables

**Document Processing Pipeline**:
- `document_processor.py`: Parses structured course documents (title/instructor/lessons), performs sentence-based text chunking
- `vector_store.py`: ChromaDB wrapper with two collections (course_catalog, course_content)
- `models.py`: Pydantic models for Course, Lesson, CourseChunk data structures

**Search & AI Integration**:
- `search_tools.py`: Tool system allowing Claude to search course content with filters
- `session_manager.py`: Conversation history management with configurable limits
- Tool-based approach: Claude decides when to search, executes searches, synthesizes results

**Frontend (`frontend/`)**:
- `script.js`: Vanilla JavaScript handling user input, API calls, session management
- Displays AI responses with markdown formatting and collapsible source attribution

### Document Format Expectations
Course documents should follow this structure:
```
Course Title: [title]
Course Link: [url]
Course Instructor: [instructor]

Lesson 1: [lesson_title]
Lesson Link: [lesson_url]
[lesson content...]

Lesson 2: [next_lesson_title]
[content...]
```

### Configuration Settings
Key settings in `config.py`:
- `CHUNK_SIZE`: 800 characters for text chunks
- `CHUNK_OVERLAP`: 100 characters between chunks
- `MAX_RESULTS`: 5 search results returned
- `MAX_HISTORY`: 2 conversation exchanges remembered
- `ANTHROPIC_MODEL`: claude-sonnet-4-20250514

### Data Storage
- **ChromaDB collections**:
  - `course_catalog`: Course metadata for semantic search
  - `course_content`: Text chunks with embeddings
- **Session storage**: In-memory conversation history
- **Vector embeddings**: Generated using `all-MiniLM-L6-v2` model

### Error Handling Patterns
- Document processing continues if individual files fail
- Vector search returns empty results gracefully
- AI tool execution includes fallback error responses
- Frontend displays loading states and error messages

The system is designed for educational content with built-in course/lesson hierarchy preservation and context-aware search capabilities.
- always use uv to run the server do not run pip directly
- make sure to use uv to manage all dependencies
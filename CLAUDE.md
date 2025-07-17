# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an AI-powered solar project intelligence pipeline that scrapes web content and extracts structured data using LLM APIs. The system processes Excel files containing project names and URLs, scrapes content using Playwright, and analyzes it through CBORG's LLM API to extract specific solar project attributes.

## Core Commands

```bash
# Main execution
python main.py                    # Run the full pipeline
python main.py --keep-checkpoint  # Run and preserve checkpoint files for debugging

# Testing
pytest                           # Run all tests
pytest tests/test_pipeline_logging.py  # Test logging system specifically
python tests/verify_logging_deployment.py  # Verify logging functionality

# Individual module testing
python model_validator.py        # Run single project validation
python tests/test_kagi.py        # Test Kagi API integration
```

## Architecture

### Core Processing Flow
1. **Excel Input**: `excel_sampler.py` reads project data from Excel files
2. **Web Scraping**: `page_tracker.py` contains `AiParser` class using Playwright for content extraction
3. **LLM Processing**: `ModelValidator` class sends scraped content to CBORG API for structured data extraction
4. **Orchestration**: `multi_project_validator.py` coordinates batch processing of multiple projects
5. **Logging**: `pipeline_logger.py` provides thread-safe CSV logging of all processing metrics
6. **Checkpointing**: `main.py` implements atomic file locking and pickle-based resume functionality

### Key Classes
- `AiParser` (`page_tracker.py`): Handles web scraping with Playwright
- `ModelValidator` (`model_validator.py`): Manages LLM API interactions and response validation
- `MultiProjectValidator` (`multi_project_validator.py`): Batch processing coordinator
- `PipelineLogger` (`pipeline_logger.py`): Thread-safe logging system

### Data Flow
- **Input**: Excel files with project names and URLs
- **Processing**: Concurrent web scraping → LLM analysis → structured extraction
- **Output**: Timestamped CSV files in `results/` directory
- **Logging**: Comprehensive metrics in `pipeline_logs/` directory
- **Checkpoints**: Resumable processing via pickle files in `checkpoints/`

## Environment Setup

### Required Environment Variables
- `CBORG_API_KEY`: API key for CBORG/LBL's LLM service

### Key Dependencies
- **Web Scraping**: playwright, playwright-stealth, beautifulsoup4, newspaper3k
- **AI/LLM**: openai, anthropic (API clients)
- **Data Processing**: pandas, numpy, openpyxl
- **Async**: asyncio, aiohttp, aiofiles
- **Testing**: pytest, pytest-playwright

## Development Notes

### Process Locking
The system uses `fcntl` file locking to prevent concurrent execution. Lock files are created in the root directory and automatically cleaned up.

### Checkpointing System
- Pickle files in `checkpoints/` allow resuming interrupted processing
- Use `--keep-checkpoint` flag to preserve checkpoint files for debugging
- Checkpoints are automatically cleaned up unless explicitly preserved

### Logging System
Comprehensive logging tracks success/failure rates, processing times, and error details for every URL processed. See `LOGGING_USAGE.md` for detailed analysis guides.

### Testing Structure
- `tests/`: Unit and integration tests
- `test_readouts/`: Test output files and sample data
- `sample_databases/`: SQLite files for testing
- `groundtruth/`: Reference data for validation

### Error Handling
The system includes robust error handling for common issues:
- Network timeouts and connection failures
- LLM API rate limiting and response validation
- Malformed input data and missing URLs
- Thread-safe logging of all error conditions
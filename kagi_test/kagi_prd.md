# Kagi Search Automation Tool Specification

## 1. Core Functionality
- **Input Structure**: Excel file with columns mapping to named variables (e.g., Column A = "City", B = "Industry")
- **Template System**: Multiple search templates per row (e.g., "Best {Industry} in {City}", "Top {City} news")
- **Processing**: Automatic batch processing of all rows with parallel execution (configurable batch size)
- **Error Handling**: Skip failed searches, log errors with row/template context to separate error log file

## 2. Search Execution
- **API Integration**: Kagi Search API integration with configurable rate limiting
- **Result Capture**: First 10 results per query (configurable via global setting) stored as columns:  
  `Template1_Result1_URL`, `Template1_Result1_Title`, ..., `Template1_Result10_URL`, ...
- **Metadata**: Include per-search timestamp, result count, API response time, and success/failure status

## 3. Output Structure
- **Preservation**: Maintain original input columns in output
- **Result Format**: Multi-column per-template results (grouped columns for each template)
- **Multi-Template**: All templates' results appear in same row with column prefixes
- **Error Log**: Separate CSV/Excel file containing:
  - Failed row number
  - Template ID
  - Error message
  - Timestamp

## 4. Configuration
- **Rate Limiting**: API call delay configuration (ms between requests)
- **Result Limits**: Global default for number of results (configurable, default=10)
- **Output**:
  - Choice of Excel or CSV format
  - Automatic filename generation with timestamp

## 5. Validation Requirements
- Input file validation:
  - Check for required template variables
  - Validate Excel formatting
  - Verify API key presence
- API response validation:
  - HTTP status checks
  - Result schema validation

## 6. Non-Functional Requirements
- **Performance**: Visual progress indicator with success/failure counts
- **Security**: API key encryption at rest and in memory
- **Audit**: Complete execution log with timestamps and metadata

## Implementation Recommendations
1. Python-based solution using:
   - `Pandas` for Excel I/O
   - `aiohttp` for async API calls
   - `pydantic` for response validation
2. Configuration file (JSON/YAML) for:
   - API credentials
   - Rate limiting
   - Default result limits
3. Modular architecture separating:
   - Template parser
   - API client
   - Result processor
   - Error handler

## Next Steps
1. Approve this spec for developer handoff
2. Identify test dataset for validation
3. Specify deployment environment requirements
4. Set up sample output data format in excel.


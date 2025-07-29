# Pipeline Logging Usage Guide

## Overview

The AI parser pipeline now includes comprehensive URL logging functionality that tracks the success and failure of both text extraction and LLM processing stages. All logging data is automatically saved to timestamped CSV files for easy analysis.

## CSV Output Format

### File Location and Naming

Log files are automatically created in the `pipeline_logs/` directory with the following naming convention:

```
pipeline_logs/pipeline_log_YYYY-MM-DD_HH-MM-SS.csv
```

**Example:** `pipeline_logs/pipeline_log_2025-06-11_12-30-45.csv`

### CSV Schema

Each CSV file contains the following columns:

| Column | Type | Description | Example Values |
|--------|------|-------------|----------------|
| `URL` | string | The URL being processed | `https://example.com/article` |
| `project_name` | string | Project identifier from your Excel file | `SolarProject_CA` |
| `timestamp` | string | ISO 8601 timestamp with timezone | `2025-06-11T12:30:45-07:00` |
| `text_extraction_status` | string | Success/failure of web scraping | `"True"` or `"False"` |
| `text_extraction_error` | string | Error details or "None" | `"None"` or `"TimeoutError: Page load timeout"` |
| `text_length` | integer | Number of characters extracted | `1542` |
| `llm_response_status` | string | Success/failure of LLM processing | `"True"` or `"False"` |
| `llm_response_error` | string | LLM error details or "None" | `"None"` or `"API rate limit exceeded"` |
| `response_time_ms` | integer | Total processing time in milliseconds | `2340` |

## Example CSV Output

### Successful Processing
```csv
URL,project_name,timestamp,text_extraction_status,text_extraction_error,text_length,llm_response_status,llm_response_error,response_time_ms
https://example.com/solar-news,SolarProject_CA,2025-06-11T12:30:45-07:00,True,None,1542,True,None,2340
https://renewableenergy.com/article,WindProject_TX,2025-06-11T12:31:02-07:00,True,None,2108,True,None,1890
```

### Failed Processing Examples
```csv
URL,project_name,timestamp,text_extraction_status,text_extraction_error,text_length,llm_response_status,llm_response_error,response_time_ms
https://broken-site.com/article,SolarProject_CA,2025-06-11T12:32:15-07:00,False,TimeoutError: Page load timeout,0,False,No text to process,5000
https://valid-site.com/article,WindProject_TX,2025-06-11T12:33:01-07:00,True,None,1200,False,API rate limit exceeded,3200
```

## How to Interpret the Data

### Text Extraction Metrics
- **`text_extraction_status`**: `"True"` means the webpage was successfully loaded and text was extracted
- **`text_extraction_error`**: Common errors include:
  - `"TimeoutError: Page load timeout"` - Site took too long to load
  - `"Navigation failed"` - URL is invalid or unreachable
  - `"None"` - No errors occurred
- **`text_length`**: Number of characters in the extracted content (title + body text)

### LLM Processing Metrics
- **`llm_response_status`**: `"True"` means the LLM successfully processed the text
- **`llm_response_error`**: Common errors include:
  - `"API rate limit exceeded"` - Too many requests to the LLM API
  - `"JSONDecodeError"` - LLM response wasn't valid JSON
  - `"None"` - No errors occurred

### Performance Metrics
- **`response_time_ms`**: Total time from start of text extraction to completion of LLM processing
- **`timestamp`**: When the URL processing began (ISO 8601 format with timezone)

## Analyzing Your Logs

### Success Rate Analysis
```python
import pandas as pd

# Load your log file
df = pd.read_csv('pipeline_logs/pipeline_log_2025-06-11_12-30-45.csv')

# Calculate success rates
text_success_rate = (df['text_extraction_status'] == 'True').mean() * 100
llm_success_rate = (df['llm_response_status'] == 'True').mean() * 100
overall_success_rate = ((df['text_extraction_status'] == 'True') & 
                       (df['llm_response_status'] == 'True')).mean() * 100

print(f"Text Extraction Success Rate: {text_success_rate:.1f}%")
print(f"LLM Processing Success Rate: {llm_success_rate:.1f}%")
print(f"Overall Success Rate: {overall_success_rate:.1f}%")
```

### Performance Analysis
```python
# Analyze processing times
successful_rows = df[(df['text_extraction_status'] == 'True') & 
                    (df['llm_response_status'] == 'True')]

avg_time = successful_rows['response_time_ms'].mean()
median_time = successful_rows['response_time_ms'].median()
max_time = successful_rows['response_time_ms'].max()

print(f"Average Processing Time: {avg_time:.0f}ms")
print(f"Median Processing Time: {median_time:.0f}ms")
print(f"Maximum Processing Time: {max_time:.0f}ms")
```

### Error Analysis
```python
# Analyze common errors
text_errors = df[df['text_extraction_status'] == 'False']['text_extraction_error'].value_counts()
llm_errors = df[df['llm_response_status'] == 'False']['llm_response_error'].value_counts()

print("Most Common Text Extraction Errors:")
print(text_errors.head())

print("\nMost Common LLM Processing Errors:")
print(llm_errors.head())
```

## Troubleshooting Guide

### Common Issues and Solutions

#### 1. No Log Files Created
**Problem**: No CSV files appear in `pipeline_logs/` directory
**Solutions**:
- Check that the `pipeline_logs/` directory exists
- Verify that the pipeline is processing URLs (not just loading configuration)
- Ensure you're running the latest version with logging enabled

#### 2. High Text Extraction Failure Rate
**Problem**: Many URLs show `text_extraction_status = "False"`
**Common Causes**:
- **Timeout errors**: Sites are loading too slowly
- **Navigation failures**: URLs are invalid or sites are down
- **JavaScript-heavy sites**: Content requires JavaScript to load

**Solutions**:
- Increase timeout settings in Playwright configuration
- Validate URLs before processing
- Consider adding wait conditions for JavaScript-heavy sites

#### 3. High LLM Processing Failure Rate
**Problem**: Many URLs show `llm_response_status = "False"`
**Common Causes**:
- **Rate limiting**: Making too many API requests too quickly
- **JSON parsing errors**: LLM responses aren't properly formatted
- **API key issues**: Invalid or expired API credentials

**Solutions**:
- Add delays between API calls
- Check API key validity and quotas
- Review prompt templates for JSON formatting requirements

#### 4. Slow Processing Times
**Problem**: `response_time_ms` values are consistently high (>10 seconds)
**Common Causes**:
- Slow website loading times
- Large amounts of text being processed
- API response delays

**Solutions**:
- Implement concurrent processing for multiple URLs
- Add timeout limits for slow-loading sites
- Consider text truncation for very long articles

## Performance Characteristics

### Expected Performance
- **Text Extraction**: 500-2000ms per URL (depending on site speed)
- **LLM Processing**: 1000-5000ms per URL (depending on text length)
- **Logging Overhead**: <1ms per URL
- **CSV File Size**: ~200 bytes per logged URL

### Scaling Considerations
- Log files are append-only and thread-safe
- Each pipeline run creates a new timestamped CSV file
- No automatic log rotation (files accumulate over time)
- Consider archiving old log files periodically

## Integration with Existing Workflow

The logging system is designed to work seamlessly with your existing pipeline:

1. **No Configuration Required**: Logging is enabled automatically
2. **No Performance Impact**: Minimal overhead added to processing
3. **No Breaking Changes**: All existing functionality remains unchanged
4. **Backward Compatible**: Works with existing checkpoint and resume functionality

## File Management

### Log File Locations
```
your-project/
├── pipeline_logs/
│   ├── pipeline_log_2025-06-11_09-15-30.csv
│   ├── pipeline_log_2025-06-11_14-22-45.csv
│   └── pipeline_log_2025-06-12_08-30-15.csv
├── main.py
├── pipeline_logger.py
└── ...
```

### Archiving Old Logs
Consider implementing a log rotation strategy:
```bash
# Archive logs older than 30 days
find pipeline_logs/ -name "*.csv" -mtime +30 -exec mv {} archived_logs/ \;
```

## Support and Troubleshooting

If you encounter issues with the logging system:

1. **Run the verification script**: `python verify_logging_deployment.py`
2. **Check log file permissions**: Ensure the pipeline can write to `pipeline_logs/`
3. **Validate CSV format**: Open log files in a spreadsheet application to check formatting
4. **Monitor disk space**: Log files accumulate over time

The logging system is designed to fail gracefully - if logging encounters an error, it won't crash the main pipeline processing.
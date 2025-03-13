import io
import os
import json
import re

import google.generativeai  as genai


api_key = os.environ.get("EMA_GOOGLE_API")
genai.configure(api_key=api_key)

MODEL_ID = "gemini-2.0-flash" # @param ["gemini-1.5-flash-latest","gemini-2.0-flash-lite","gemini-2.0-flash","gemini-2.0-pro-exp-02-05"] {"allow-input":true}

# Define system instruction
sys_instruction = """You are an analyst that conducts company research.
You are given a company name, and you will work on a company report. You have access
to Google Search to look up company news, updates and metrics to write research reports.

When given a company name, identify key aspects to research, look up that information
and then write a concise company report.

Feel free to plan your work and talk about it, but when you start writing the report,
put a line of dashes (---) to demarcate the report itself, and say nothing else after
the report has finished.
"""

# Create a model instance
model = genai.GenerativeModel(
    model_name=MODEL_ID,
    system_instruction=sys_instruction,
    generation_config={"temperature": 0}
)

# Company to research
COMPANY = "Apple Inc."

# Generate content with Google Search enabled
response_stream = model.generate_content(
    COMPANY,
    stream=True,
    tools=[{"google_search": {}}]
)

# Process the streaming response
report = io.StringIO()
for chunk in response_stream:
    # Process each chunk
    if hasattr(chunk, 'text'):
        # Print the chunk text
        print(chunk.text, end="", flush=True)

        # Find and save the report itself
        if report.tell() > 0:
            # If already recording the report, continue
            report.write(chunk.text)
        elif m := re.search(r'(^|\n)-+\n(.*)$', chunk.text, re.DOTALL):
            # Found the start of the report
            report.write(m.group(2))

# Print the final report
print("\n\nFinal Report:")
print(report.getvalue())


import os
import sqlite3 

from page_tracker import AiParser
from pathlib import Path


pv_mag = 'https://pv-magazine-usa.com/category/installations/commercial-industrial-pv/'
with open('solar-projects-prompt-2.txt', 'r') as file:
    prompt = file.read()

api_key = os.environ.get('CYCLOGPT_API_KEY')
api_url = "https://api.cyclogpt.lbl.gov"
model = 'lbl/cyclogpt:chat-v1'

tool = AiParser(publication_url=pv_mag,
                api_key=api_key,
                api_url=api_url,
                model=model,
                prompt=prompt)

articles = tool.get_articles_urls()

data = tool.articles_parser(urls=articles,
                            max_limit=15)

breakpoint()

# create a connection to the SQLite database
conn = sqlite3.connect("my_database.db")
cursor = conn.cursor()

# create a table with the desired columns
cursor.execute("""
    CREATE TABLE IF NOT EXISTS projects (
        url TEXT PRIMARY KEY,
        name TEXT,
        gen INTEGER,
        storage INTEGER,
        technology TEXT,
        location TEXT,
        project_description TEXT
    );
""")


for item in data:
    if item:
        for k, v in item.items():
            if k.startswith("https:"):
                url = k
                name = v.get("name")
                gen = v.get("gen")
                storage = v.get("storage")
                technology = v.get("technology")
                location = v.get("location")
                project_description = v.get("project_description")
                cursor.execute("""
                    INSERT OR IGNORE INTO projects (
                        url,
                        name,
                        gen,
                        storage,
                        technology,
                        location,
                        project_description
                    ) VALUES (?, ?, ?, ?, ?, ?, ?);
                """, (url, name, gen, storage, technology, location, project_description))

# commit the changes
conn.commit()

# close the connection
conn.close() 




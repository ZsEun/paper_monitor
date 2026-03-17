#!/usr/bin/env python3
"""Debug script to see what HTML we're getting from IEEE"""

import requests
from bs4 import BeautifulSoup

url = "https://ieeexplore.ieee.org/xpl/mostRecentIssue.jsp?punumber=15"

session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
})

response = session.get(url, timeout=10)
soup = BeautifulSoup(response.content, 'html.parser')

# Save HTML to file for inspection
with open('ieee_page.html', 'w', encoding='utf-8') as f:
    f.write(soup.prettify())

print(f"HTML saved to ieee_page.html")
print(f"Page title: {soup.title.string if soup.title else 'No title'}")
print(f"\nLooking for common IEEE Xplore elements...")

# Look for various possible selectors
selectors_to_try = [
    ('div.List-results-items', 'List results items'),
    ('xpl-results-item', 'XPL results item'),
    ('article', 'Article tags'),
    ('div.result-item', 'Result items'),
    ('h3', 'H3 headers (titles)'),
    ('a[href*="/document/"]', 'Document links'),
]

for selector, description in selectors_to_try:
    elements = soup.select(selector)
    print(f"  {description} ({selector}): {len(elements)} found")

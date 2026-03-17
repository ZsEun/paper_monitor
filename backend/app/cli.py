#!/usr/bin/env python3
"""CLI tool for running monitoring tasks"""

import sys
from app.scrapers.monitor import JournalMonitor

def main():
    if len(sys.argv) < 2:
        print("Usage: python -m app.cli [monitor|digest]")
        sys.exit(1)
    
    command = sys.argv[1]
    monitor = JournalMonitor()
    
    if command == "monitor":
        print("Running journal monitoring...")
        papers = monitor.monitor_journals()
        print(f"Completed! Found {len(papers) if papers else 0} papers")
    
    elif command == "digest":
        print("Generating weekly digest...")
        digest = monitor.generate_digest()
        if digest:
            print(f"Digest generated successfully!")
            print(f"Papers: {len(digest['papers'])}")
            print(f"Topics: {len(digest['topicGroups'])}")
        else:
            print("No digest generated")
    
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)

if __name__ == "__main__":
    main()

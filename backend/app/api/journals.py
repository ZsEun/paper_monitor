from fastapi import APIRouter, HTTPException, status
from app.models.schemas import Journal, JournalCreate
from app.utils.storage import read_json_file, write_json_file
from typing import List
from datetime import datetime
import uuid

router = APIRouter()

JOURNALS_FILE = "journals.json"

@router.get("", response_model=List[Journal])
def get_journals():
    journals = read_json_file(JOURNALS_FILE)
    return list(journals.values())

@router.post("", response_model=Journal)
def create_journal(journal: JournalCreate):
    journals = read_json_file(JOURNALS_FILE)
    
    journal_id = str(uuid.uuid4())
    new_journal = {
        "id": journal_id,
        "name": journal.name,
        "platform": journal.platform,
        "url": journal.url,
        "addedAt": datetime.now().strftime("%Y-%m-%d"),
        "isSubscribed": True
    }
    
    journals[journal_id] = new_journal
    write_json_file(JOURNALS_FILE, journals)
    
    return new_journal

@router.put("/{journal_id}", response_model=Journal)
def update_journal(journal_id: str, journal: JournalCreate):
    journals = read_json_file(JOURNALS_FILE)

    if journal_id not in journals:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Journal not found"
        )

    journals[journal_id]["name"] = journal.name
    journals[journal_id]["platform"] = journal.platform
    journals[journal_id]["url"] = journal.url
    write_json_file(JOURNALS_FILE, journals)

    return journals[journal_id]


@router.delete("/{journal_id}")
def delete_journal(journal_id: str):
    journals = read_json_file(JOURNALS_FILE)
    
    if journal_id not in journals:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Journal not found"
        )
    
    del journals[journal_id]
    write_json_file(JOURNALS_FILE, journals)
    
    return {"message": "Journal deleted successfully"}

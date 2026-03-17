from fastapi import APIRouter, HTTPException, status
from app.models.schemas import Credential, CredentialCreate
from app.utils.storage import read_json_file, write_json_file
from app.utils.security import get_password_hash
from typing import List
from datetime import datetime
import uuid

router = APIRouter()

CREDENTIALS_FILE = "credentials.json"

@router.get("", response_model=List[Credential])
def get_credentials():
    credentials = read_json_file(CREDENTIALS_FILE)
    return list(credentials.values())

@router.get("/{journal_id}", response_model=List[Credential])
def get_credentials_by_journal(journal_id: str):
    credentials = read_json_file(CREDENTIALS_FILE)
    journal_creds = [cred for cred in credentials.values() if cred["journalId"] == journal_id]
    return journal_creds

@router.post("", response_model=Credential)
def create_credential(credential: CredentialCreate):
    credentials = read_json_file(CREDENTIALS_FILE)
    
    credential_id = str(uuid.uuid4())
    
    # Hash the password for storage
    hashed_password = get_password_hash(credential.password)
    
    new_credential = {
        "id": credential_id,
        "journalId": credential.journalId,
        "journalName": credential.journalName,
        "username": credential.username,
        "credentialType": credential.credentialType,
        "password": hashed_password,  # Store hashed
        "maskedValue": "*" * 8,  # Masked for display
        "addedAt": datetime.now().strftime("%Y-%m-%d")
    }
    
    credentials[credential_id] = new_credential
    write_json_file(CREDENTIALS_FILE, credentials)
    
    # Return without password
    return {
        "id": credential_id,
        "journalId": credential.journalId,
        "journalName": credential.journalName,
        "username": credential.username,
        "credentialType": credential.credentialType,
        "maskedValue": "*" * 8,
        "addedAt": new_credential["addedAt"]
    }

@router.delete("/{credential_id}")
def delete_credential(credential_id: str):
    credentials = read_json_file(CREDENTIALS_FILE)
    
    if credential_id not in credentials:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Credential not found"
        )
    
    del credentials[credential_id]
    write_json_file(CREDENTIALS_FILE, credentials)
    
    return {"message": "Credential deleted successfully"}

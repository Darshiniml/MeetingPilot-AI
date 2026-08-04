"""Contact routes for managing personal contact intelligence."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from app.core.dependencies import CurrentUser, get_contact_service
from app.contacts.contact_service import ContactService
from app.contacts.schemas import (
    ContactCreate,
    ContactUpdate,
    ContactResponse,
    ContactSearchRequest,
    ContactImportRequest,
)

router = APIRouter(prefix="/contacts", tags=["contacts"])

@router.post("", response_model=ContactResponse, status_code=status.HTTP_201_CREATED)
def create_contact(
    data: ContactCreate,
    service: ContactService = Depends(get_contact_service)
) -> ContactResponse:
    """Create a new contact."""
    return service.create_contact(data)

@router.get("", response_model=list[ContactResponse])
def list_contacts(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    service: ContactService = Depends(get_contact_service)
) -> list[ContactResponse]:
    """List contacts with optional pagination."""
    return service.list_contacts(limit=limit, offset=offset)

@router.put("/{id}", response_model=ContactResponse)
def update_contact(
    id: int,
    data: ContactUpdate,
    service: ContactService = Depends(get_contact_service)
) -> ContactResponse:
    """Update an existing contact."""
    contact = service.update_contact(id, data)
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found.")
    return contact

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_contact(
    id: int,
    service: ContactService = Depends(get_contact_service)
) -> None:
    """Delete a contact."""
    success = service.delete_contact(id)
    if not success:
        raise HTTPException(status_code=404, detail="Contact not found.")

@router.post("/import", response_model=list[ContactResponse])
def import_contacts(
    request: ContactImportRequest,
    service: ContactService = Depends(get_contact_service)
) -> list[ContactResponse]:
    """Import contacts from CSV content or sync from Google Contacts."""
    try:
        if request.provider == "google":
            return service.sync_google_contacts()
        elif request.provider == "csv":
            if not request.csv_content:
                raise HTTPException(status_code=422, detail="csv_content is required for CSV imports.")
            return service.import_contacts_csv(request.csv_content)
        else:
            raise HTTPException(status_code=400, detail="Invalid provider. Choose 'csv' or 'google'.")
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

@router.post("/search", response_model=list[ContactResponse])
def search_contacts(
    request: ContactSearchRequest,
    service: ContactService = Depends(get_contact_service)
) -> list[ContactResponse]:
    """Perform fuzzy name, email, company search on contacts."""
    return service.search_contacts(request.query, limit=request.limit)

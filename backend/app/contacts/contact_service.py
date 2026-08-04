import csv
import io
import httpx
from datetime import datetime, timezone, timedelta
from typing import Any
from sqlalchemy.orm import Session

from app.contacts.contact_model import Contact
from app.contacts.contact_repository import ContactRepository
from app.contacts.schemas import ContactCreate, ContactUpdate
from app.integrations.google_calendar.token_store import TokenStore
from app.integrations.google_calendar.oauth import GoogleOAuthService

class ContactService:
    """Service layer orchestrating Contacts business logic, including CSV import and merged Google Contacts sync."""

    def __init__(self, session: Session, user_id: int) -> None:
        self.session = session
        self.user_id = user_id
        self.repo = ContactRepository(session, user_id)
        self._token_store = TokenStore(session)
        self._oauth = GoogleOAuthService()

    def get_contact(self, contact_id: int) -> Contact | None:
        return self.repo.get_contact_by_id(contact_id)

    def list_contacts(self, limit: int = 100, offset: int = 0) -> list[Contact]:
        return self.repo.list_contacts(limit=limit, offset=offset)

    def create_contact(self, data: ContactCreate) -> Contact:
        contact = Contact(
            display_name=data.display_name,
            first_name=data.first_name,
            last_name=data.last_name,
            company=data.company,
            job_title=data.job_title,
            email=data.email,
            phone=data.phone,
            linkedin_url=data.linkedin_url,
            is_favorite=data.is_favorite,
            notes=data.notes
        )
        return self.repo.create_contact(contact)

    def update_contact(self, contact_id: int, data: ContactUpdate) -> Contact | None:
        contact = self.repo.get_contact_by_id(contact_id)
        if not contact:
            return None
            
        update_data = data.model_dump(exclude_unset=True)
        for key, val in update_data.items():
            setattr(contact, key, val)
            
        return self.repo.update_contact(contact)

    def delete_contact(self, contact_id: int) -> bool:
        return self.repo.delete_contact(contact_id)

    def search_contacts(self, query: str, limit: int = 10) -> list[Contact]:
        return self.repo.search_contacts(query, limit)

    def import_contacts_csv(self, csv_content: str) -> list[Contact]:
        """Parse raw CSV input, create contacts locally, mapping headers flexibly."""
        f = io.StringIO(csv_content.strip())
        reader = csv.DictReader(f)
        imported = []
        
        for row in reader:
            mapped = {}
            for k, v in row.items():
                if not k:
                    continue
                k_low = k.lower().replace(" ", "_").replace("-", "_")
                if "display_name" in k_low or k_low == "name":
                    mapped["display_name"] = v.strip()
                elif "first_name" in k_low or k_low == "first":
                    mapped["first_name"] = v.strip()
                elif "last_name" in k_low or k_low == "last":
                    mapped["last_name"] = v.strip()
                elif "company" in k_low or k_low == "org":
                    mapped["company"] = v.strip()
                elif "job" in k_low or "title" in k_low:
                    mapped["job_title"] = v.strip()
                elif "email" in k_low:
                    mapped["email"] = v.strip()
                elif "phone" in k_low or k_low == "tel":
                    mapped["phone"] = v.strip()
                elif "notes" in k_low or k_low == "comment":
                    mapped["notes"] = v.strip()
                    
            if "display_name" not in mapped:
                first = mapped.get("first_name", "")
                last = mapped.get("last_name", "")
                if first or last:
                    mapped["display_name"] = f"{first} {last}".strip()
                elif mapped.get("email"):
                    mapped["display_name"] = mapped["email"].split("@")[0]
                else:
                    continue
                    
            # Check if email duplicate exists
            email = mapped.get("email")
            existing = None
            if email:
                existing = self.repo.get_contact_by_email(email)
                
            if existing:
                # Merge CSV values
                for k, v in mapped.items():
                    if v and not getattr(existing, k, None):
                        setattr(existing, k, v)
                self.repo.update_contact(existing)
                imported.append(existing)
            else:
                contact = Contact(
                    display_name=mapped["display_name"],
                    first_name=mapped.get("first_name"),
                    last_name=mapped.get("last_name"),
                    company=mapped.get("company"),
                    job_title=mapped.get("job_title"),
                    email=email,
                    phone=mapped.get("phone"),
                    notes=mapped.get("notes")
                )
                self.repo.create_contact(contact)
                imported.append(contact)
                
        return imported

    def _get_google_access_token(self) -> str:
        decrypted = self._token_store.get_decrypted_tokens(self.user_id)
        if not decrypted:
            raise RuntimeError("Google Account not connected.")
            
        token_record = self._token_store.get_token(self.user_id)
        scopes = token_record.scopes or ""
        if "contacts.readonly" not in scopes:
            raise RuntimeError("Google Contacts permissions ('contacts.readonly' scope) not authorized.")

        expires_at = decrypted["expires_at"]
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        now = datetime.now(timezone.utc)
        if now + timedelta(minutes=1) >= expires_at:
            refresh_token = decrypted["refresh_token"]
            if not refresh_token:
                raise RuntimeError("Refresh token missing. Re-authorization required.")
            refreshed = self._oauth.refresh_access_token(refresh_token)
            self._token_store.save_token(
                user_id=self.user_id,
                google_email=decrypted["google_email"],
                access_token=refreshed["access_token"],
                refresh_token=refresh_token,
                expires_at=refreshed["expires_at"],
                scopes=scopes
            )
            return refreshed["access_token"]

        return decrypted["access_token"]

    def sync_google_contacts(self) -> list[Contact]:
        """Fetch Google Contacts and merge them safely with local contacts, avoiding overwriting manual local edits."""
        token = self._get_google_access_token()
        url = "https://people.googleapis.com/v1/people/me/connections"
        headers = {"Authorization": f"Bearer {token}"}
        params = {
            "personFields": "names,emailAddresses,phoneNumbers,organizations,biographies",
            "pageSize": 100
        }

        with httpx.Client() as client:
            resp = client.get(url, headers=headers, params=params)
            if resp.status_code != 200:
                raise RuntimeError(f"Google People API failed: {resp.text}")
                
            connections = resp.json().get("connections", [])
            synced = []

            for conn in connections:
                # 1. Parse connection attributes
                name_obj = conn.get("names", [{}])[0]
                display_name = name_obj.get("displayName", "Unnamed Google Contact")
                first_name = name_obj.get("givenName")
                last_name = name_obj.get("familyName")
                
                email = conn.get("emailAddresses", [{}])[0].get("value")
                phone = conn.get("phoneNumbers", [{}])[0].get("value")
                
                org_obj = conn.get("organizations", [{}])[0]
                company = org_obj.get("name")
                job_title = org_obj.get("title")
                
                notes = conn.get("biographies", [{}])[0].get("value")

                # 2. Check if a local record already exists by email
                existing = None
                if email:
                    existing = self.repo.get_contact_by_email(email)
                else:
                    existing = self.repo.get_contact_by_name_and_company(display_name, company)

                if existing:
                    # Merge logic: preserve local edits
                    # Merge names/phone/company/job only if local field is empty
                    if not existing.first_name:
                        existing.first_name = first_name
                    if not existing.last_name:
                        existing.last_name = last_name
                    if not existing.phone:
                        existing.phone = phone
                    if not existing.company:
                        existing.company = company
                    if not existing.job_title:
                        existing.job_title = job_title
                        
                    # notes merging: append Google notes if not present locally
                    if notes and notes not in (existing.notes or ""):
                        existing.notes = f"{existing.notes or ''}\n[Google Contact Import]: {notes}".strip()
                        
                    # We do NOT overwrite is_favorite or linkedin_url since those are likely local edits.
                    self.repo.update_contact(existing)
                    synced.append(existing)
                else:
                    # Create new local contact
                    new_contact = Contact(
                        display_name=display_name,
                        first_name=first_name,
                        last_name=last_name,
                        company=company,
                        job_title=job_title,
                        email=email,
                        phone=phone,
                        notes=notes,
                        is_favorite=False
                    )
                    self.repo.create_contact(new_contact)
                    synced.append(new_contact)

            return synced

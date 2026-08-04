from difflib import SequenceMatcher
from typing import Any
from app.contacts.contact_model import Contact
from app.contacts.contact_repository import ContactRepository

class ContactMatcher:
    """Weighted matching engine for contact resolution."""

    def __init__(self, repo: ContactRepository) -> None:
        self.repo = repo

    def calculate_match_score(self, query_name: str, contact: Contact, context_text: str | None = None) -> float:
        """Calculate weighted match score combining name similarity, company match, email match, and frequency."""
        score = 0.0
        
        # 1. Name Similarity (Weight = 0.70)
        name_ratios = []
        name_ratios.append(SequenceMatcher(None, query_name.lower(), contact.display_name.lower()).ratio())
        if contact.first_name:
            name_ratios.append(SequenceMatcher(None, query_name.lower(), contact.first_name.lower()).ratio())
        if contact.last_name:
            name_ratios.append(SequenceMatcher(None, query_name.lower(), contact.last_name.lower()).ratio())
        if contact.first_name and contact.last_name:
            full_name = f"{contact.first_name} {contact.last_name}"
            name_ratios.append(SequenceMatcher(None, query_name.lower(), full_name.lower()).ratio())
            
        name_score = max(name_ratios) if name_ratios else 0.0
        if query_name.lower() == contact.display_name.lower():
            name_score = 1.0
            
        score += name_score * 0.70

        # 2. Company Match (Weight = 0.15)
        company_score = 0.0
        if contact.company:
            if context_text and contact.company.lower() in context_text.lower():
                company_score = 1.0
            elif contact.company.lower() in query_name.lower():
                company_score = 1.0
        score += company_score * 0.15

        # 3. Email Match (Weight = 0.05)
        email_score = 0.0
        if contact.email and "@" in query_name and query_name.lower() == contact.email.lower():
            email_score = 1.0
        score += email_score * 0.05

        # 4. Meeting Frequency (Weight = 0.10)
        freq = 0
        if contact.email:
            freq = self.repo.get_invitation_frequency(contact.email)
        freq_score = min(freq / 10.0, 1.0)
        score += freq_score * 0.10

        # Favorite Boost
        if contact.is_favorite and score > 0.0:
            score = min(score + 0.05, 1.0)

        return score

    def resolve_attendee(self, attendee_query: str, contacts: list[Contact], context_text: str | None = None) -> dict[str, Any]:
        """Resolve a query name or email string against contacts, returning structured resolution metrics."""
        # If query is direct email address, resolve it immediately
        if "@" in attendee_query and "." in attendee_query:
            return {
                "input_name": attendee_query,
                "resolved_email": attendee_query,
                "status": "RESOLVED",
                "confidence_score": 1.0,
                "source": "INPUT",
                "candidates": []
            }

        candidates = []
        for contact in contacts:
            score = self.calculate_match_score(attendee_query, contact, context_text)
            if score >= 0.50:
                candidates.append({
                    "contact_id": contact.id,
                    "display_name": contact.display_name,
                    "email": contact.email,
                    "company": contact.company,
                    "confidence_score": round(score, 2)
                })

        candidates.sort(key=lambda x: x["confidence_score"], reverse=True)

        if not candidates:
            return {
                "input_name": attendee_query,
                "resolved_email": None,
                "status": "NOT_FOUND",
                "confidence_score": 0.0,
                "source": "CONTACTS",
                "candidates": []
            }

        top_candidate = candidates[0]
        is_clear_winner = False
        
        if len(candidates) == 1:
            if top_candidate["confidence_score"] >= 0.60:
                is_clear_winner = True
        else:
            diff = top_candidate["confidence_score"] - candidates[1]["confidence_score"]
            if diff >= 0.15 or top_candidate["confidence_score"] >= 0.85:
                is_clear_winner = True

        if is_clear_winner:
            return {
                "input_name": attendee_query,
                "resolved_email": top_candidate["email"],
                "status": "RESOLVED",
                "confidence_score": top_candidate["confidence_score"],
                "source": "CONTACTS",
                "candidates": candidates
            }
        else:
            return {
                "input_name": attendee_query,
                "resolved_email": None,
                "status": "AMBIGUOUS",
                "confidence_score": top_candidate["confidence_score"],
                "source": "CONTACTS",
                "candidates": candidates
            }

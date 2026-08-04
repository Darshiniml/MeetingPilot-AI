"""Email HTML templates loader."""

import os
from app.scheduler.schemas import MeetingDetails

def load_template(
    template_name: str,
    details: MeetingDetails,
    meet_link: str,
    body_content: str
) -> str:
    """Load an HTML template file and substitute meeting variables."""
    # Find templates directory relative to this file
    current_dir = os.path.dirname(os.path.abspath(__file__))
    template_path = os.path.join(current_dir, "templates", f"{template_name}.html")

    if not os.path.exists(template_path):
        raise FileNotFoundError(f"Email template file not found: {template_path}")

    with open(template_path, "r", encoding="utf-8") as f:
        html = f.read()

    # Dynamic variables mapping
    replacements = {
        "{{ title }}": details.title,
        "{{ date }}": details.date,
        "{{ time }}": details.time,
        "{{ duration }}": details.duration,
        "{{ timezone }}": details.timezone,
        "{{ meet_link }}": meet_link,
        "{{ content }}": body_content
    }

    for key, val in replacements.items():
        html = html.replace(key, str(val))

    return html

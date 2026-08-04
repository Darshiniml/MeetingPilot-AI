from __future__ import annotations

import re
import logging
from typing import Any

logger = logging.getLogger(__name__)

class BrowserDetector:
    """Inspects active browser window metadata strings to match meeting domain indicators."""
    
    def __init__(self) -> None:
        pass

    def extract_meeting_url(self, window_info: dict[str, Any]) -> str | None:
        """Audits the window title text to extract recognized meeting web page urls."""
        title = window_info.get("title", "")
        proc = window_info.get("process_name", "").lower()
        
        # Browsers list
        browsers = ["chrome.exe", "msedge.exe", "firefox.exe", "safari.exe", "opera.exe", "brave.exe"]
        if not any(b in proc for b in browsers) and "browser" not in proc:
            return None
            
        # Standard URL patterns matched inside brackets or raw strings
        patterns = [
            r"(meet\.google\.com/[a-z0-9\-]+)",
            r"(teams\.microsoft\.com/[a-zA-Z0-9\-\_\/\%\&\?\=]+)",
            r"([a-zA-Z0-9\-]+\.zoom\.us/[j|s]/[0-9\?]+)",
            r"(web\.webex\.com/[a-zA-Z0-9\-\_\/]+)",
            r"(discord\.com/channels/[0-9\/]+)"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, title, re.IGNORECASE)
            if match:
                url = match.group(1)
                logger.debug("Matched browser meeting URL: %s", url)
                return url
                
        # Fallback check on titles containing direct keywords
        if "meet.google.com" in title.lower():
            return "meet.google.com"
        if "zoom.us" in title.lower():
            return "zoom.us"
        if "teams.microsoft" in title.lower():
            return "teams.microsoft.com"
            
        return None

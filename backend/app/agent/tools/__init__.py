"""Adapters that expose existing application capabilities to the agent."""

from .action_item_tool import ActionItemTool
from .calendar_tool import CalendarTool
from .contact_tool import ContactTool
from .gmail_tool import GmailTool
from .meeting_history_tool import MeetingHistoryTool
from .rag_chat_tool import RAGChatTool
from .scheduler_tool import SchedulerTool
from .summary_tool import SummaryTool
from .transcript_tool import TranscriptTool
from .vision_tool import VisionTool

ALL_TOOL_TYPES = (
    SummaryTool, TranscriptTool, MeetingHistoryTool, ActionItemTool, SchedulerTool,
    CalendarTool, GmailTool, ContactTool, RAGChatTool, VisionTool,
)

__all__ = ["ALL_TOOL_TYPES", "ActionItemTool", "CalendarTool", "ContactTool", "GmailTool", "MeetingHistoryTool", "RAGChatTool", "SchedulerTool", "SummaryTool", "TranscriptTool", "VisionTool"]

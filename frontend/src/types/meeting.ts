export type ActionItem = {
  id: number;
  task: string;
  owner: string | null;
  due_date: string | null;
  priority: string | null;
  status: string;
};

export type TranscriptEntry = {
  chunk_index: number;
  text: string;
  start_seconds: number;
  end_seconds: number;
  language: string;
  confidence: number | null;
  speaker_id?: string | null;
  speaker_name?: string | null;
  speaker_confidence?: number | null;
};

export type MeetingDetail = {
  id: number;
  title: string;
  status: string;
  start_time: string | null;
  end_time: string | null;
  duration: number | null;
  transcript: TranscriptEntry[];
  summary: string | null;
  action_items: ActionItem[];
};

export type MeetingHistoryItem = {
  id: number;
  title: string;
  start_time: string | null;
  end_time: string | null;
  duration: number | null;
  transcript_count: number;
  summary_available: boolean;
  participants: number;
  action_items: number;
  meeting_status: string;
  created_at: string;
};

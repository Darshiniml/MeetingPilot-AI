import { useEffect, useState } from "react";
import api from "../../services/api";
import type { MeetingHistoryItem } from "../../types/meeting";
import { Search, ChevronRight, ChevronLeft, RefreshCw } from "lucide-react";
import { Card } from "../ui/Card";
import { Badge } from "../ui/Badge";
import { Button } from "../ui/Button";

type MeetingHistoryPanelProps = {
  selectedMeetingId: number | null;
  onSelectMeeting: (meetingId: number) => void;
};

function MeetingHistoryPanel({ selectedMeetingId, onSelectMeeting }: MeetingHistoryPanelProps) {
  const [meetings, setMeetings] = useState<MeetingHistoryItem[]>([]);
  const [offset, setOffset] = useState(0);
  const [total, setTotal] = useState(0);
  const [search, setSearch] = useState("");
  const [date, setDate] = useState("");
  const [participantCount, setParticipantCount] = useState("");
  const [refreshTrigger, setRefreshTrigger] = useState(0);
  const limit = 8;

  useEffect(() => {
    api.get(`/meetings?offset=${offset}&limit=${limit}`)
      .then((response) => {
        setMeetings(response.data.items || []);
        setTotal(response.data.total || 0);
      })
      .catch(console.error);
  }, [offset, refreshTrigger, selectedMeetingId]);

  const handleRefresh = () => {
    setRefreshTrigger(prev => prev + 1);
  };

  const filteredMeetings = meetings.filter((meeting) => (
    meeting.title.toLowerCase().includes(search.toLowerCase())
    && (!date || meeting.start_time?.startsWith(date))
    && (!participantCount || meeting.participants === Number(participantCount))
  ));

  return (
    <Card hoverEffect={false} className="p-6 flex flex-col gap-5 text-left h-full">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-base font-bold text-slate-100 font-display">Meeting History</h2>
          <p className="text-xs text-zinc-500 mt-0.5">Filter and review previous audio recordings.</p>
        </div>
        <button
          onClick={handleRefresh}
          className="p-1.5 rounded-lg bg-zinc-900 border border-zinc-800 text-zinc-400 hover:text-white transition-colors cursor-pointer"
          title="Refresh History"
        >
          <RefreshCw size={14} />
        </button>
      </div>

      {/* Filters */}
      <div className="space-y-2">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500 w-3.5 h-3.5" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search meetings..."
            className="w-full bg-zinc-950 border border-zinc-800 rounded-lg pl-9 pr-3 py-1.5 text-xs text-slate-100 placeholder-zinc-500 focus:outline-none focus:border-indigo-500"
          />
        </div>
        
        <div className="grid grid-cols-2 gap-2">
          <input
            type="date"
            value={date}
            onChange={(e) => setDate(e.target.value)}
            className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-1.5 text-xs text-zinc-400 focus:outline-none focus:border-indigo-500"
          />
          <input
            type="number"
            min="0"
            value={participantCount}
            onChange={(e) => setParticipantCount(e.target.value)}
            placeholder="Participants"
            className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-1.5 text-xs text-slate-100 placeholder-zinc-500 focus:outline-none focus:border-indigo-500"
          />
        </div>
      </div>

      {/* Meetings Grid */}
      <div className="space-y-2 overflow-y-auto pr-1 flex-1 min-h-[300px]">
        {filteredMeetings.map((meeting) => {
          const isSelected = selectedMeetingId === meeting.id;
          return (
            <button
              key={meeting.id}
              onClick={() => onSelectMeeting(meeting.id)}
              className={`w-full rounded-xl p-3.5 text-left border transition-all duration-150 cursor-pointer flex flex-col gap-2 ${
                isSelected
                  ? "border-indigo-500/30 bg-indigo-600/5 text-white"
                  : "border-zinc-800/80 bg-zinc-950/20 text-zinc-400 hover:border-zinc-700 hover:bg-zinc-800/20"
              }`}
            >
              <div className="flex items-center justify-between gap-3 font-semibold text-xs text-slate-200">
                <span className="truncate">{meeting.title} (ID: {meeting.id})</span>
                <span className="font-mono text-[10px] text-zinc-500 shrink-0">
                  {((meeting.duration || 0) / 60).toFixed(1)}m
                </span>
              </div>
              
              <div className="flex items-center justify-between text-[10px] text-zinc-500">
                <span>{meeting.transcript_count || 0} transcript chunks (Raw: {meeting.transcript_count})</span>
                {meeting.summary_available ? (
                  <Badge variant="success">Summary Ready</Badge>
                ) : (
                  <Badge variant="secondary">Audio Captured</Badge>
                )}
              </div>
            </button>
          );
        })}
        {filteredMeetings.length === 0 && (
          <p className="text-zinc-500 text-xs py-10 text-center">No meetings match these filters.</p>
        )}
      </div>

      {/* Pagination */}
      <div className="flex items-center justify-between border-t border-zinc-900 pt-3">
        <Button
          variant="secondary"
          size="sm"
          disabled={offset === 0}
          onClick={() => setOffset(Math.max(0, offset - limit))}
          className="gap-1 px-2.5 py-1 text-[11px]"
        >
          <ChevronLeft size={12} />
          Prev
        </Button>
        <span className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider">
          Offset {offset} / {total}
        </span>
        <Button
          variant="secondary"
          size="sm"
          disabled={offset + limit >= total}
          onClick={() => setOffset(offset + limit)}
          className="gap-1 px-2.5 py-1 text-[11px]"
        >
          Next
          <ChevronRight size={12} />
        </Button>
      </div>
    </Card>
  );
}

export default MeetingHistoryPanel;

import type { MeetingDetail } from "../../types/meeting";
import { Clock, Users, Type } from "lucide-react";
import { Card } from "../ui/Card";

type MeetingStatsPanelProps = { meeting: MeetingDetail | null };

function MeetingStatsPanel({ meeting }: MeetingStatsPanelProps) {
  if (!meeting) return null;
  
  const wordCount = meeting.transcript.reduce(
    (total, chunk) => total + chunk.text.trim().split(/\s+/).filter(Boolean).length,
    0
  );

  return (
    <Card hoverEffect={false} className="p-6 text-left">
      <h3 className="font-display font-bold text-xs tracking-wide text-zinc-500 uppercase mb-4">Metadata</h3>
      
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {/* Duration */}
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-zinc-950 flex items-center justify-center text-indigo-400 border border-zinc-900 shrink-0">
            <Clock size={14} />
          </div>
          <div className="flex flex-col">
            <span className="text-[10px] font-semibold text-zinc-500 uppercase">Duration</span>
            <span className="text-xs font-bold text-slate-300">
              {((meeting.duration || 0) / 60).toFixed(1)} min
            </span>
          </div>
        </div>

        {/* Participants */}
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-zinc-950 flex items-center justify-center text-indigo-400 border border-zinc-900 shrink-0">
            <Users size={14} />
          </div>
          <div className="flex flex-col">
            <span className="text-[10px] font-semibold text-zinc-500 uppercase">Speakers</span>
            <span className="text-xs font-bold text-slate-300">
              {/* Extract unique speakers count */}
              {new Set(meeting.transcript.map(c => c.speaker_name).filter(Boolean)).size || 1}
            </span>
          </div>
        </div>

        {/* Word Count */}
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-zinc-950 flex items-center justify-center text-indigo-400 border border-zinc-900 shrink-0">
            <Type size={14} />
          </div>
          <div className="flex flex-col">
            <span className="text-[10px] font-semibold text-zinc-500 uppercase">Words</span>
            <span className="text-xs font-bold text-slate-300">{wordCount}</span>
          </div>
        </div>

        {/* Action Items */}
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-zinc-950 flex items-center justify-center text-indigo-400 border border-zinc-900 shrink-0">
            <Users size={14} />
          </div>
          <div className="flex flex-col">
            <span className="text-[10px] font-semibold text-zinc-500 uppercase">Action items</span>
            <span className="text-xs font-bold text-slate-300">{meeting.action_items.length}</span>
          </div>
        </div>

      </div>
    </Card>
  );
}

export default MeetingStatsPanel;

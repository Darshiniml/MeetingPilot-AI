import { useState } from "react";
import type { MeetingDetail } from "../../types/meeting";
import { Search, Copy, Download, Check, MessageCircle } from "lucide-react";
import { Card } from "../ui/Card";
import { Avatar } from "../ui/Avatar";
import { Badge } from "../ui/Badge";
import { Button } from "../ui/Button";

type MeetingDetailPanelProps = { meeting: MeetingDetail | null };

function MeetingDetailPanel({ meeting }: MeetingDetailPanelProps) {
  const [search, setSearch] = useState("");
  const [copied, setCopied] = useState(false);

  if (!meeting) {
    return (
      <Card hoverEffect={false} className="p-6 text-center text-zinc-500 py-16">
        <MessageCircle size={28} className="mx-auto mb-2 text-zinc-600" />
        <p className="text-sm font-semibold">No Meeting Selected</p>
        <p className="text-xs text-zinc-500 mt-1">Select a session from the history log to inspect transcripts and summaries.</p>
      </Card>
    );
  }

  const transcript = meeting.transcript.filter((chunk) =>
    chunk.text.toLowerCase().includes(search.toLowerCase())
  );
  
  const text = meeting.transcript
    .map((chunk) => `[${chunk.start_seconds.toFixed(1)}s] ${chunk.speaker_name || "UNKNOWN"}: ${chunk.text}`)
    .join("\n");

  const copy = () => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const download = () => {
    const link = document.createElement("a");
    link.href = URL.createObjectURL(new Blob([text], { type: "text/plain" }));
    link.download = `meeting-${meeting.id}-transcript.txt`;
    link.click();
    URL.revokeObjectURL(link.href);
  };

  return (
    <Card hoverEffect={false} className="p-6 flex flex-col gap-4 text-left">
      <div className="flex flex-col md:flex-row md:items-start justify-between border-b border-zinc-900 pb-4 gap-3">
        <div className="text-left">
          <h2 className="text-base font-bold text-slate-100 font-display">{meeting.title}</h2>
          <p className="text-[10px] text-zinc-500 mt-0.5 font-semibold uppercase tracking-wider">
            {meeting.status} · {((meeting.duration || 0) / 60).toFixed(1)} minutes
          </p>
        </div>
        
        <div className="flex items-center gap-2">
          <Button variant="secondary" size="sm" onClick={copy} className="gap-1.5 text-xs py-1 px-2.5">
            {copied ? <Check size={12} className="text-emerald-400" /> : <Copy size={12} />}
            Copy
          </Button>
          <Button variant="secondary" size="sm" onClick={download} className="gap-1.5 text-xs py-1 px-2.5">
            <Download size={12} />
            Download
          </Button>
        </div>
      </div>

      {/* Search filter */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500 w-3.5 h-3.5" />
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Filter transcript segments..."
          className="w-full bg-zinc-950 border border-zinc-800 rounded-lg pl-9 pr-3 py-1.5 text-xs text-slate-100 placeholder-zinc-500 focus:outline-none focus:border-indigo-500"
        />
      </div>

      {/* Transcript Chat style logs */}
      <div className="max-h-72 overflow-y-auto bg-zinc-950/40 border border-zinc-900 rounded-xl p-4 space-y-3.5">
        {transcript.map((chunk) => {
          const speakerName = chunk.speaker_name && chunk.speaker_name !== 'Unknown' ? chunk.speaker_name : 'Primary Speaker';
          const confidence = chunk.confidence !== null ? chunk.confidence : 1.0;
          return (
            <div key={chunk.chunk_index} className="flex items-start gap-3 border-b border-zinc-900/40 pb-3 last:border-none last:pb-0 text-left">
              <Avatar name={speakerName} size="sm" className="mt-0.5" />
              <div className="flex-1">
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold text-slate-300">{speakerName}</span>
                    {confidence < 0.65 && (
                      <Badge variant="warning">Low Conf</Badge>
                    )}
                  </div>
                  <span className="text-[10px] font-mono text-zinc-500">{chunk.start_seconds.toFixed(0)}s</span>
                </div>
                <p className="text-xs text-zinc-400 leading-relaxed font-sans">{chunk.text || "[No speech detected]"}</p>
              </div>
            </div>
          );
        })}
        {transcript.length === 0 && (
          <p className="text-zinc-500 text-xs py-6 text-center">No speech matches search criteria.</p>
        )}
      </div>
    </Card>
  );
}

export default MeetingDetailPanel;

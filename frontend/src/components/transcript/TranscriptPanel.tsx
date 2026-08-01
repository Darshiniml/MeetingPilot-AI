import { useEffect, useMemo, useRef, useState } from "react";
import api from "../../services/api";

type TranscriptEntry = { id: number; meeting_id: number; chunk_index: number; segment_index?: number; text: string; start_seconds: number; end_seconds: number; language: string; confidence: number | null; speaker_id?: string | null; speaker_name?: string | null; speaker_confidence?: number | null };

type TranscriptPanelProps = { onMeetingStopped: (meetingId: number) => void };

function TranscriptPanel({ onMeetingStopped }: TranscriptPanelProps) {
  const [running, setRunning] = useState(false);
  const [transcripts, setTranscripts] = useState<TranscriptEntry[]>([]);
  const listRef = useRef<HTMLDivElement | null>(null);

  const fetchStatus = async () => {
    try {
      const response = await api.get("/meeting/status");
      setRunning(response.data.running);
    } catch (error) {
      console.error(error);
    }
  };

  useEffect(() => {
    fetchStatus();
  }, []);

  useEffect(() => {
    const socket = new WebSocket("ws://127.0.0.1:8000/ws/transcript");

    socket.addEventListener("message", (event) => {
      const data = JSON.parse(event.data);
      if (data.type !== "transcript") {
        return;
      }

      console.debug("Frontend received transcript", data.transcript);
      setTranscripts((current) => [...current, data.transcript]);
    });

    return () => {
      socket.close();
    };
  }, []);

  useEffect(() => {
    if (listRef.current) {
      listRef.current.scrollTop = listRef.current.scrollHeight;
    }
  }, [transcripts]);

  const startMeeting = async () => {
    try {
      await api.post("/meeting/start");
      setRunning(true);
    } catch (error) {
      console.error(error);
    }
  };

  const stopMeeting = async () => {
    try {
      const response = await api.post("/meeting/stop");
      setRunning(false);
      const meetingId = response.headers["x-meeting-id"];
      if (meetingId) {
        onMeetingStopped(Number(meetingId));
      }
    } catch (error) {
      console.error(error);
    }
  };

  const transcriptItems = useMemo(() => {
    return transcripts.map((entry) => (
      <div key={entry.id} className="rounded-lg border border-slate-800 bg-slate-950/80 p-3 text-sm text-slate-300">
        <div className="mb-1 flex items-center justify-between text-xs uppercase tracking-wide text-slate-500">
          <span className="flex items-center gap-2">
            {entry.speaker_name && entry.speaker_name !== "Unknown" ? (
              <>
                <span className="text-slate-300 font-semibold">{entry.speaker_name}</span>
                {entry.speaker_confidence !== null && entry.speaker_confidence !== undefined && entry.speaker_confidence < 0.5 && (
                  <span className="bg-yellow-900/50 text-yellow-500 px-1.5 py-0.5 rounded text-[10px]">Low Conf</span>
                )}
              </>
            ) : (
              <span>Unknown Speaker</span>
            )}
          </span>
          <span>{entry.start_seconds.toFixed(1)}s</span>
        </div>
        <div>{entry.text}</div>
      </div>
    ));
  }, [transcripts]);

  return (
    <div className="bg-slate-900 rounded-xl p-6 h-full flex flex-col">
      <h2 className="text-2xl font-bold mb-6">🎙 Live Transcript</h2>

      <div className="mb-6">
        {running ? (
          <span className="text-green-400 font-semibold">🟢 Meeting is Running</span>
        ) : (
          <span className="text-red-400 font-semibold">🔴 Meeting Stopped</span>
        )}
      </div>

      <div className="flex gap-4 mb-8">
        <button
          onClick={startMeeting}
          className="bg-green-600 hover:bg-green-700 px-5 py-2 rounded-lg"
        >
          ▶ Start Meeting
        </button>

        <button
          onClick={stopMeeting}
          className="bg-red-600 hover:bg-red-700 px-5 py-2 rounded-lg"
        >
          ■ Stop Meeting
        </button>
      </div>

      <div ref={listRef} className="flex-1 overflow-y-auto bg-slate-950 rounded-lg p-4 space-y-3 text-slate-400">
        {transcriptItems.length > 0 ? (
          transcriptItems
        ) : (
          running ? "🎤 Listening to the meeting..." : "Waiting for meeting to start..."
        )}
      </div>
    </div>
  );
}

export default TranscriptPanel;

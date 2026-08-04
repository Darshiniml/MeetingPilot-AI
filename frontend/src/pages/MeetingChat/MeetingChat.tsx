import { useEffect, useMemo, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import api from "../../services/api";
import type { MeetingHistoryItem } from "../../types/meeting";
import { type ChatMessage, useMeetingChatStore } from "../../store/meetingChatStore";
import {
  MessageSquare,
  Search,
  Trash2,
  RotateCw,
  Copy,
  Check,
  Send,
  Video,
  Loader2,
  Sparkles
} from "lucide-react";
import { motion } from "framer-motion";
import { Button } from "../../components/ui/Button";
import { Avatar } from "../../components/ui/Avatar";
import { useToastStore } from "../../store/useToastStore";

const suggestions = [
  "What decisions were made in this session?",
  "List all action items and their assignees.",
  "Provide a concise bullet summary.",
  "Were there any risks or deadlines discussed?"
];

const createMessage = (role: ChatMessage["role"], content: string, status?: ChatMessage["status"]): ChatMessage => ({
  id: crypto.randomUUID(),
  role,
  content,
  createdAt: new Date().toISOString(),
  status
});

function MeetingChat() {
  const [meetings, setMeetings] = useState<MeetingHistoryItem[]>([]);
  const [search, setSearch] = useState("");
  const [input, setInput] = useState("");
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const endRef = useRef<HTMLDivElement>(null);
  
  const {
    selectedMeetingId,
    conversations,
    recentMeetingIds,
    selectMeeting,
    addMessage,
    updateMessage,
    clearConversation
  } = useMeetingChatStore();
  
  const { addToast } = useToastStore();

  const messages = selectedMeetingId ? conversations[selectedMeetingId] ?? [] : [];

  useEffect(() => {
    api.get("/meetings?offset=0&limit=100")
      .then((response) => setMeetings(response.data.items || []))
      .catch(() => addToast('error', 'Load Failed', 'Unable to load meeting history directory.'));
  }, []);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const visibleMeetings = useMemo(() =>
    meetings.filter((meeting) => meeting.title.toLowerCase().includes(search.toLowerCase())),
    [meetings, search]
  );

  const recentMeetings = recentMeetingIds
    .map((id) => meetings.find((meeting) => meeting.id === id))
    .filter((meeting): meeting is MeetingHistoryItem => Boolean(meeting));

  const send = async (question = input) => {
    if (!selectedMeetingId || !question.trim() || messages.some((message) => message.status === "pending")) return;
    const user = createMessage("user", question.trim());
    const assistant = createMessage("assistant", "", "pending");
    addMessage(selectedMeetingId, user);
    addMessage(selectedMeetingId, assistant);
    setInput("");
    
    try {
      const response = await api.post("/chat", { meeting_id: selectedMeetingId, question: user.content });
      const answer = String(response.data.answer ?? "").trim();
      if (!answer) throw new Error("The local model returned an empty response.");
      updateMessage(selectedMeetingId, assistant.id, { content: answer, status: undefined });
    } catch (requestError) {
      const detail = typeof requestError === "object" && requestError && "response" in requestError
        ? (requestError as { response?: { data?: { detail?: string } } }).response?.data?.detail
        : undefined;
      updateMessage(selectedMeetingId, assistant.id, {
        content: detail ?? "Unable to reach the local AI service. Verify Ollama and the embedding engine are active, then try again.",
        status: "error"
      });
    }
  };

  const regenerate = (messageIndex: number) => {
    const previousUser = [...messages.slice(0, messageIndex)].reverse().find((message) => message.role === "user");
    if (previousUser) void send(previousUser.content);
  };

  const handleCopy = (id: string, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
    addToast('success', 'Copied', 'Message content saved to clipboard.');
  };

  return (
    <main className="flex-1 p-5 xl:p-6 overflow-hidden flex flex-col min-h-0 text-left">
      <div className="grid flex-1 grid-cols-1 overflow-hidden rounded-2xl border border-zinc-900 bg-zinc-950/20 lg:grid-cols-[20rem_minmax(0,1fr)]">
        
        {/* Left Side: Meetings List */}
        <aside className="border-b border-zinc-900 p-5 lg:border-b-0 lg:border-r flex flex-col gap-4 overflow-hidden h-[75svh]">
          <div>
            <h2 className="text-sm font-bold text-slate-100 font-display flex items-center gap-2">
              <MessageSquare size={16} className="text-indigo-400" />
              Copilot Chat Rooms
            </h2>
            <p className="text-[10px] text-zinc-500 mt-0.5">Select a logged session to chat with the RAG assistant.</p>
          </div>

          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500 w-3.5 h-3.5" />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search rooms..."
              className="w-full bg-zinc-950 border border-zinc-800 rounded-lg pl-9 pr-3 py-1.5 text-xs text-slate-100 placeholder-zinc-500 focus:outline-none focus:border-indigo-500"
            />
          </div>

          <div className="flex-1 overflow-y-auto space-y-4 pr-1">
            {recentMeetings.length > 0 && (
              <section className="space-y-2">
                <p className="text-[9px] font-bold uppercase tracking-wider text-zinc-500">Recently Opened</p>
                {recentMeetings.map((meeting) => (
                  <MeetingButton
                    key={`recent-${meeting.id}`}
                    meeting={meeting}
                    selected={meeting.id === selectedMeetingId}
                    onClick={() => selectMeeting(meeting.id)}
                  />
                ))}
              </section>
            )}

            <section className="space-y-2">
              <p className="text-[9px] font-bold uppercase tracking-wider text-zinc-500">All Rooms</p>
              <div className="space-y-1.5">
                {visibleMeetings.map((meeting) => (
                  <MeetingButton
                    key={meeting.id}
                    meeting={meeting}
                    selected={meeting.id === selectedMeetingId}
                    onClick={() => selectMeeting(meeting.id)}
                  />
                ))}
                {visibleMeetings.length === 0 && (
                  <p className="text-xs text-zinc-500 py-6 text-center">No active chat sessions found.</p>
                )}
              </div>
            </section>
          </div>
        </aside>

        {/* Right Side: Chat Window */}
        <section className="flex flex-col h-[75svh] overflow-hidden bg-zinc-950/10">
          <header className="flex items-center justify-between border-b border-zinc-900 px-5 py-4 shrink-0">
            <div className="text-left">
              <h3 className="text-sm font-bold text-slate-200 font-display">
                {selectedMeetingId
                  ? meetings.find((meeting) => meeting.id === selectedMeetingId)?.title ?? `Meeting Room #${selectedMeetingId}`
                  : "Select a Session"}
              </h3>
              <p className="text-[10px] text-zinc-500 mt-0.5">
                Ask grounded questions about transcription logs. Context is loaded statelessly.
              </p>
            </div>
            {selectedMeetingId && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => clearConversation(selectedMeetingId)}
                className="gap-1 text-xs border border-zinc-800 hover:bg-zinc-800"
              >
                <Trash2 size={12} className="text-zinc-400" />
                Clear
              </Button>
            )}
          </header>

          {/* Messages stream */}
          <div className="flex-1 overflow-y-auto p-5 space-y-4">
            {!selectedMeetingId ? (
              <div className="h-full flex flex-col items-center justify-center text-zinc-500 py-16">
                <MessageSquare size={32} className="text-zinc-700 mb-3" />
                <span className="text-sm font-semibold">Select a Meeting Room</span>
                <span className="text-xs text-zinc-500 mt-1 max-w-[200px] text-center">Select a recorded meeting from the left sidebar to query details.</span>
              </div>
            ) : (
              <>
                {messages.length === 0 && (
                  <div className="max-w-md mx-auto pt-10 text-center space-y-4">
                    <Sparkles className="text-indigo-400 animate-pulse mx-auto" size={24} />
                    <div>
                      <h4 className="text-sm font-bold text-slate-200">How can I assist you with this meeting?</h4>
                      <p className="text-xs text-zinc-500 mt-0.5">Click a quick template command below to begin.</p>
                    </div>
                    <div className="grid gap-2 grid-cols-1 sm:grid-cols-2 text-left">
                      {suggestions.map((prompt) => (
                        <button
                          key={prompt}
                          onClick={() => void send(prompt)}
                          className="p-3 text-xs text-zinc-400 hover:text-indigo-400 bg-zinc-950/60 rounded-xl border border-zinc-900 hover:border-indigo-500/30 transition-all cursor-pointer leading-relaxed"
                        >
                          {prompt}
                        </button>
                      ))}
                    </div>
                  </div>
                )}
                
                {messages.map((message, index) => (
                  <motion.article
                    key={message.id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className={`max-w-3xl flex gap-3.5 p-4 rounded-xl text-left border ${
                      message.role === "user"
                        ? "ml-auto bg-indigo-600 border-indigo-500/20 text-white"
                        : message.status === "error"
                        ? "border-red-500/20 bg-red-500/5 text-red-200"
                        : "bg-zinc-900 border-zinc-800 text-zinc-300"
                    }`}
                  >
                    <Avatar name={message.role === "user" ? "User" : "AI"} size="sm" className="mt-0.5" />
                    
                    <div className="flex-1 overflow-hidden">
                      <div className="flex items-center justify-between text-[10px] opacity-60 mb-2 font-bold uppercase tracking-wider">
                        <span>{message.role === "user" ? "You" : "MeetingPilot AI"}</span>
                        {message.status === "pending" && (
                          <span className="flex items-center gap-1.5 text-indigo-400 font-bold">
                            <Loader2 size={10} className="animate-spin" />
                            Thinking...
                          </span>
                        )}
                      </div>
                      
                      {message.status === "pending" ? (
                        <div className="space-y-2 py-1.5">
                          <div className="h-2 w-3/4 rounded bg-zinc-800 animate-pulse" />
                          <div className="h-2 w-1/2 rounded bg-zinc-800 animate-pulse" />
                        </div>
                      ) : (
                        <div className="prose prose-invert prose-xs max-w-none break-words leading-relaxed font-sans text-xs">
                          <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
                        </div>
                      )}

                      {message.role === "assistant" && !message.status && (
                        <div className="mt-3.5 flex gap-2 border-t border-zinc-900 pt-2 shrink-0">
                          <button
                            onClick={() => handleCopy(message.id, message.content)}
                            className="text-[10px] font-semibold text-zinc-500 hover:text-slate-200 flex items-center gap-1 cursor-pointer"
                          >
                            {copiedId === message.id ? <Check size={10} className="text-emerald-400" /> : <Copy size={10} />}
                            Copy response
                          </button>
                          <button
                            onClick={() => regenerate(index)}
                            className="text-[10px] font-semibold text-zinc-500 hover:text-slate-200 flex items-center gap-1 cursor-pointer"
                          >
                            <RotateCw size={10} />
                            Regenerate
                          </button>
                        </div>
                      )}
                    </div>
                  </motion.article>
                ))}
                <div ref={endRef} />
              </>
            )}
          </div>

          {/* Text Input area */}
          <div className="border-t border-zinc-900 p-4 bg-zinc-950/20 shrink-0">
            <div className="relative">
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    void send();
                  }
                }}
                disabled={!selectedMeetingId}
                placeholder={
                  selectedMeetingId
                    ? "Ask a question about this meeting... (Enter to send, Shift+Enter for newline)"
                    : "Select a chat room room to start"
                }
                rows={2}
                className="w-full bg-zinc-950 border border-zinc-800 rounded-xl p-3 pl-4 pr-12 text-xs text-slate-100 placeholder-zinc-500 focus:outline-none focus:border-indigo-500 transition-all resize-none"
              />
              <button
                onClick={() => void send()}
                disabled={!selectedMeetingId || !input.trim() || messages.some((m) => m.status === "pending")}
                className="absolute right-3.5 bottom-4 w-7 h-7 rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 text-white flex items-center justify-center transition-all cursor-pointer shrink-0"
              >
                <Send size={12} fill="white" />
              </button>
            </div>
          </div>
        </section>

      </div>
    </main>
  );
}

function MeetingButton({ meeting, selected, onClick }: { meeting: MeetingHistoryItem; selected: boolean; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className={`w-full rounded-xl p-3 text-left transition-all duration-150 cursor-pointer flex items-center gap-3 border ${
        selected
          ? "border-indigo-500/30 bg-indigo-600/5 text-white"
          : "border-zinc-900/60 bg-zinc-950/40 text-zinc-400 hover:border-zinc-800 hover:bg-zinc-800/20"
      }`}
    >
      <div className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 border ${
        selected ? 'bg-indigo-600/10 border-indigo-500/20 text-indigo-400' : 'bg-zinc-900 border-zinc-800 text-zinc-500'
      }`}>
        <Video size={14} />
      </div>
      <div className="flex-1 overflow-hidden text-left">
        <p className="text-xs font-bold text-slate-200 truncate">{meeting.title} (ID: {meeting.id})</p>
        <p className="mt-0.5 text-[9px] text-zinc-500 truncate font-mono">
          {((meeting.duration || 0) / 60).toFixed(1)}m · {meeting.transcript_count} chunks (Raw: {meeting.transcript_count})
        </p>
      </div>
    </button>
  );
}

export default MeetingChat;

import { useState } from "react";
import api from "../../services/api";
import { Sparkles, MessageSquare, Loader2 } from "lucide-react";
import { Card } from "../ui/Card";
import { Button } from "../ui/Button";

type ChatPanelProps = { meetingId: number | null };

function ChatPanel({ meetingId }: ChatPanelProps) {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const askQuestion = async () => {
    if (!meetingId || !question.trim()) return;
    setLoading(true);
    setAnswer(null);
    try {
      const response = await api.post("/chat", { meeting_id: meetingId, question });
      setAnswer(response.data.answer);
    } catch (error) {
      console.error(error);
      setAnswer("Unable to answer this question. Ensure your local Ollama embedding model and LLM service are active.");
    } finally {
      setLoading(false);
    }
  };

  if (!meetingId) return null;

  return (
    <Card hoverEffect={false} className="p-6 text-left">
      <div className="flex items-center gap-2 mb-4 border-b border-zinc-900 pb-3">
        <MessageSquare className="text-indigo-400" size={16} />
        <h2 className="text-sm font-bold text-slate-200 font-display">Meeting Assistant</h2>
      </div>

      <div className="space-y-4">
        <textarea
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          disabled={loading}
          placeholder="Ask a question about key agreements, metrics, or follow-ups in this meeting..."
          className="w-full bg-zinc-950 border border-zinc-800 rounded-lg p-3 text-xs text-slate-100 placeholder-zinc-500 focus:outline-none focus:border-indigo-500 transition-all resize-none"
          rows={3}
        />
        
        <Button
          variant="primary"
          size="sm"
          onClick={askQuestion}
          disabled={loading || !question.trim()}
          className="gap-2"
        >
          {loading ? (
            <>
              <Loader2 size={12} className="animate-spin" />
              Thinking...
            </>
          ) : (
            <>
              <Sparkles size={12} />
              Ask AI
            </>
          )}
        </Button>
        
        {answer && (
          <div className="p-4 bg-zinc-950 border border-zinc-900 rounded-xl text-xs text-zinc-300 leading-relaxed font-sans whitespace-pre-wrap">
            {answer}
          </div>
        )}
      </div>
    </Card>
  );
}

export default ChatPanel;

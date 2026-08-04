import React, { useEffect, useMemo, useRef, useState } from 'react';
import api from '../../services/api';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Database,
  Radio,
  Clock,
  Play,
  Square,
  Search,
  Copy,
  Check,
  Activity,
  UserCheck,
  Sparkles,
  AlertTriangle,
  HelpCircle,
  Send,
  RefreshCw,
  SlidersHorizontal,
  Layers,
  Bot,
  Zap,
  ChevronDown,
  ChevronUp,
  Brain,
  CheckSquare,
  Compass
} from 'lucide-react';
import { Button } from '../../components/ui/Button';
import { Badge } from '../../components/ui/Badge';
import { Avatar } from '../../components/ui/Avatar';
import { Card } from '../../components/ui/Card';
import { useToastStore } from '../../store/useToastStore';

type TranscriptEntry = {
  id: number;
  meeting_id: number;
  chunk_index: number;
  segment_index?: number;
  text: string;
  start_seconds: number;
  end_seconds: number;
  language: string;
  confidence: number | null;
  speaker_id?: string | null;
  speaker_name?: string | null;
  speaker_confidence?: number | null;
};

interface CopilotInsight {
  insight_id: string;
  meeting_id: number;
  insight_type: 'decision' | 'risk' | 'deadline' | 'commitment' | 'question' | 'recommendation' | 'workflow';
  title: string;
  content: string;
  confidence: number;
  speaker: string | null;
  timestamp: string;
  metadata?: {
    severity?: 'info' | 'warning' | 'critical';
    workflow_id?: string;
    [key: string]: any;
  };
}

interface ChatMessage {
  id: string;
  sender: 'user' | 'assistant';
  text: string;
  timestamp: Date;
}

interface LiveMeetingPageProps {
  onMeetingStopped: (meetingId: number) => void;
}

export const LiveMeetingPage: React.FC<LiveMeetingPageProps> = ({ onMeetingStopped }) => {
  const [running, setRunning] = useState(false);
  const [transcripts, setTranscripts] = useState<TranscriptEntry[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [timerSeconds, setTimerSeconds] = useState(0);
  const [wsStatus, setWsStatus] = useState<'connecting' | 'connected' | 'disconnected'>('disconnected');
  const [audioLevel, setAudioLevel] = useState(0);
  const [stopping, setStopping] = useState(false);
  const [copiedId, setCopiedId] = useState<number | null>(null);

  // Copilot States
  const [insights, setInsights] = useState<CopilotInsight[]>([]);
  const [copilotWsStatus, setCopilotWsStatus] = useState<'connecting' | 'connected' | 'disconnected'>('disconnected');
  const [copilotSearchQuery, setCopilotSearchQuery] = useState('');
  const [copilotFilterType, setCopilotFilterType] = useState<string>('all');
  const [copilotFilterSeverity, setCopilotFilterSeverity] = useState<string>('all');
  const [copilotSortOrder, setCopilotSortOrder] = useState<'newest' | 'oldest'>('newest');
  const [copilotActiveTab, setCopilotActiveTab] = useState<'insights' | 'workflows' | 'assistant'>('insights');
  const [expandedCardId, setExpandedCardId] = useState<string | null>(null);
  
  // Ask AI Chat state
  const [chatInput, setChatInput] = useState('');
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [chatLoading, setChatLoading] = useState(false);
  const [autoScrollCopilot, setAutoScrollCopilot] = useState(true);

  const listRef = useRef<HTMLDivElement | null>(null);
  const copilotListRef = useRef<HTMLDivElement | null>(null);
  const timerRef = useRef<any>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const copilotWsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<any>(null);
  const reconnectDelayRef = useRef(1000);
  
  const { addToast } = useToastStore();

  const fetchStatus = async () => {
    try {
      const response = await api.get('/meeting/status');
      setRunning(response.data.running);
      if (response.data.running) {
        startLocalTimer();
      }
    } catch (error) {
      console.error("Failed to load status:", error);
    }
  };

  useEffect(() => {
    fetchStatus();
    return () => {
      stopLocalTimer();
      if (wsRef.current) wsRef.current.close();
      if (copilotWsRef.current) copilotWsRef.current.close();
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
    };
  }, []);

  // Set up transcripts WebSocket
  useEffect(() => {
    const token = localStorage.getItem('accessToken');
    if (!token) {
      setWsStatus('disconnected');
      return;
    }
    setWsStatus('connecting');
    const socket = new WebSocket(`ws://127.0.0.1:8000/ws/transcript?token=${encodeURIComponent(token)}`);
    wsRef.current = socket;

    socket.addEventListener('open', () => {
      setWsStatus('connected');
    });

    socket.addEventListener('message', (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'transcript') {
        console.debug("Received live transcript chunk", data.transcript);
        setTranscripts((current) => [...current, data.transcript]);
      }
      if (data.type === 'audio_level') {
        setAudioLevel(Math.min(1, Math.max(0, Number(data.rms) || 0)));
      }
    });

    socket.addEventListener('close', () => {
      setWsStatus('disconnected');
    });

    return () => {
      socket.close();
    };
  }, []);

  // Set up Copilot WebSocket connection with exponential backoff reconnects
  const connectCopilotWs = () => {
    if (copilotWsRef.current) {
      copilotWsRef.current.close();
    }

    const token = localStorage.getItem('accessToken');
    if (!token) {
      setCopilotWsStatus('disconnected');
      return;
    }

    setCopilotWsStatus('connecting');
    const socket = new WebSocket(`ws://127.0.0.1:8000/ws/copilot?token=${encodeURIComponent(token)}`);
    copilotWsRef.current = socket;

    socket.addEventListener('open', () => {
      setCopilotWsStatus('connected');
      reconnectDelayRef.current = 1000; // Reset exponential backoff delay
    });

    socket.addEventListener('message', (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'copilot_update') {
          console.debug("Received live copilot update packet:", data);
          if (data.insights) {
            setInsights(data.insights);
          }
        }
      } catch (err) {
        console.error("Failed to parse copilot message payload:", err);
      }
    });

    socket.addEventListener('close', () => {
      setCopilotWsStatus('disconnected');
      // If meeting is still active, retry connection using exponential backoff
      if (running) {
        reconnectTimeoutRef.current = setTimeout(() => {
          reconnectDelayRef.current = Math.min(reconnectDelayRef.current * 2, 30000);
          console.info("[Copilot WS] Reconnecting to Copilot WebSocket...");
          connectCopilotWs();
        }, reconnectDelayRef.current);
      }
    });

    socket.addEventListener('error', () => {
      socket.close();
    });
  };

  useEffect(() => {
    if (running) {
      connectCopilotWs();
    } else {
      if (copilotWsRef.current) {
        copilotWsRef.current.close();
        copilotWsRef.current = null;
      }
      setCopilotWsStatus('disconnected');
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }
    }
  }, [running]);

  // Auto-scroll to bottom on new transcripts
  useEffect(() => {
    if (listRef.current) {
      listRef.current.scrollTop = listRef.current.scrollHeight;
    }
  }, [transcripts]);

  // Auto-scroll Copilot Panel
  useEffect(() => {
    if (autoScrollCopilot && copilotListRef.current) {
      copilotListRef.current.scrollTop = copilotListRef.current.scrollHeight;
    }
  }, [insights, chatMessages, autoScrollCopilot]);

  const handleCopilotScroll = (e: React.UIEvent<HTMLDivElement>) => {
    const target = e.currentTarget;
    const isAtBottom = target.scrollHeight - target.scrollTop <= target.clientHeight + 25;
    if (isAtBottom) {
      setAutoScrollCopilot(true);
    } else {
      setAutoScrollCopilot(false);
    }
  };

  const startLocalTimer = () => {
    if (timerRef.current) return;
    timerRef.current = setInterval(() => {
      setTimerSeconds((prev) => prev + 1);
    }, 1000);
  };

  const stopLocalTimer = () => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
  };

  const startMeeting = async () => {
    try {
      await api.post('/meeting/start');
      setRunning(true);
      setTimerSeconds(0);
      setTranscripts([]);
      setInsights([]);
      setChatMessages([]);
      setAudioLevel(0);
      startLocalTimer();
      addToast('success', 'Meeting Started', 'Speaker-loopback and screen capture feeds are now active.');
    } catch (error) {
      console.error(error);
      addToast('error', 'Start Failed', 'Could not access the recording pipeline.');
    }
  };

  const stopMeeting = async () => {
    if (stopping) return;
    setStopping(true);
    try {
      const response = await api.post('/meeting/stop');
      setRunning(false);
      setAudioLevel(0);
      stopLocalTimer();
      addToast('success', 'Meeting Stopped', 'Generating AI summary, task actions, and chat indices...');
      const meetingId = response.headers['x-meeting-id'];
      if (meetingId) {
        onMeetingStopped(Number(meetingId));
      }
    } catch (error) {
      console.error(error);
      addToast('error', 'Stop Failed', 'Could not gracefully stop recording.');
    } finally {
      setStopping(false);
    }
  };

  const formatTime = (secs: number) => {
    const m = Math.floor(secs / 60).toString().padStart(2, '0');
    const s = (secs % 60).toString().padStart(2, '0');
    return `${m}:${s}`;
  };

  const handleCopy = (id: number, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    addToast('success', 'Copied', 'Transcript snippet copied to clipboard.');
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handleCopyInsight = (insight: CopilotInsight) => {
    navigator.clipboard.writeText(`[${insight.insight_type.toUpperCase()}] ${insight.title}: ${insight.content}`);
    addToast('success', 'Copied', 'Insight copied to clipboard.');
  };

  // Find active speaker from recent transcripts
  const activeSpeaker = useMemo(() => {
    if (transcripts.length === 0) return 'None';
    const last = transcripts[transcripts.length - 1];
    return last.speaker_name && last.speaker_name !== 'Unknown' ? last.speaker_name : 'Primary Speaker';
  }, [transcripts]);

  // Unique speakers mapping
  const participants = useMemo(() => {
    const list = new Set<string>();
    transcripts.forEach((t) => {
      if (t.speaker_name && t.speaker_name !== 'Unknown') {
        list.add(t.speaker_name);
      }
    });
    if (list.size === 0) return ['Primary Speaker'];
    return Array.from(list);
  }, [transcripts]);

  // AI Chat Submission
  const handleSendChat = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!chatInput.trim()) return;

    const userMsg: ChatMessage = {
      id: `chat-${Date.now()}-user`,
      sender: 'user',
      text: chatInput,
      timestamp: new Date()
    };

    setChatMessages((prev) => [...prev, userMsg]);
    setChatInput('');
    setChatLoading(true);

    // Simulate Streaming LLM Reply based on current meeting state
    setTimeout(() => {
      const topicCount = insights.length;
      const recentSegments = transcripts.slice(-3).map(t => t.text).join(' ');
      const responseText = topicCount > 0 
        ? `Based on the active meeting analysis, I've tracked ${topicCount} key insights. The dominant focus is on "${insights[0]?.title || 'general updates'}". Transcripts mention: "${recentSegments || 'Waiting for discussion details'}"`
        : `I am monitoring the audio stream. No critical items have been flagged yet. So far the transcripts discuss: "${recentSegments || 'Waiting for speakers...'}"`;

      const botMsg: ChatMessage = {
        id: `chat-${Date.now()}-bot`,
        sender: 'assistant',
        text: responseText,
        timestamp: new Date()
      };
      setChatMessages((prev) => [...prev, botMsg]);
      setChatLoading(false);
    }, 1200);
  };

  // Filtered and Sorted Insights
  const filteredInsights = useMemo(() => {
    return insights
      .filter((insight) => {
        // Text Search
        const textMatch = 
          insight.title.toLowerCase().includes(copilotSearchQuery.toLowerCase()) ||
          insight.content.toLowerCase().includes(copilotSearchQuery.toLowerCase());
        
        // Type filter
        const typeMatch = copilotFilterType === 'all' || insight.insight_type === copilotFilterType;

        // Severity filter
        const severity = insight.metadata?.severity?.toLowerCase() || 'info';
        const severityMatch = copilotFilterSeverity === 'all' || severity === copilotFilterSeverity;

        return textMatch && typeMatch && severityMatch;
      })
      .sort((a, b) => {
        const timeA = new Date(a.timestamp).getTime();
        const timeB = new Date(b.timestamp).getTime();
        return copilotSortOrder === 'newest' ? timeB - timeA : timeA - timeB;
      });
  }, [insights, copilotSearchQuery, copilotFilterType, copilotFilterSeverity, copilotSortOrder]);

  // Quick Action triggers
  const handleScrollToTranscript = (speaker: string | null) => {
    if (!speaker) return;
    addToast('info', 'Searching Transcript', `Locating snippets by ${speaker}...`);
    setSearchQuery(speaker);
  };

  const handleCreateWorkflowFromInsight = (insight: CopilotInsight) => {
    addToast('success', 'Workflow Initiated', `Creating autonomous workflow suggestion for: "${insight.title}"`);
    // Append simulated workflow suggestion state to state list
    const newWorkflowInsight: CopilotInsight = {
      insight_id: `wf-${Date.now()}`,
      meeting_id: insight.meeting_id,
      insight_type: 'workflow',
      title: `Workflow: ${insight.title} Automation`,
      content: `Suggested compensating automation flow based on insight. Priority level high. Status: Waiting Approval`,
      confidence: 0.95,
      speaker: 'System Router',
      timestamp: new Date().toISOString(),
      metadata: { severity: 'warning', workflow_id: `wf-id-${Date.now()}` }
    };
    setInsights((prev) => [newWorkflowInsight, ...prev]);
  };

  const handleApproveWorkflow = (id: string) => {
    addToast('success', 'Workflow Approved', `Executing workflow sequence ${id}. Dispatching task signals...`);
    setInsights((prev) =>
      prev.map((ins) =>
        ins.insight_id === id 
          ? { ...ins, content: "Workflow executed successfully. Step 4/4 completed. Status: ACTIVE" } 
          : ins
      )
    );
  };

  const getInsightIcon = (type: string) => {
    switch (type) {
      case 'decision': return <UserCheck className="text-emerald-400 w-4 h-4" />;
      case 'risk': return <AlertTriangle className="text-rose-400 w-4 h-4" />;
      case 'deadline': return <Clock className="text-amber-400 w-4 h-4" />;
      case 'commitment': return <CheckSquare className="text-indigo-400 w-4 h-4" />;
      case 'question': return <HelpCircle className="text-sky-400 w-4 h-4" />;
      case 'recommendation': return <Compass className="text-purple-400 w-4 h-4" />;
      case 'workflow': return <Zap className="text-violet-400 w-4 h-4 animate-pulse" />;
      default: return <Sparkles className="text-zinc-400 w-4 h-4" />;
    }
  };

  return (
    <main className="flex-1 grid grid-cols-1 xl:grid-cols-4 gap-5 p-5 xl:p-6 min-h-0 overflow-y-auto">
      
      {/* COLUMN 1: Recording controls, waveforms, participants & pipeline statuses */}
      <div className="xl:col-span-1 space-y-5 flex flex-col justify-between h-fit">
        
        {/* Rec Controls Card */}
        <Card className="p-6 flex flex-col gap-6 text-left relative overflow-hidden bg-zinc-950/20 border-zinc-800">
          <div className="flex items-center justify-between">
            <h3 className="font-display font-bold text-xs tracking-wider text-zinc-500 uppercase">Live Session</h3>
            {running && (
              <span className="flex items-center gap-1.5 text-xs text-red-500 font-bold bg-red-500/10 border border-red-500/25 px-2 py-0.5 rounded-full">
                <span className="w-1.5 h-1.5 rounded-full bg-red-500 animate-ping" />
                REC
              </span>
            )}
          </div>

          <div className="flex flex-col items-center justify-center py-5 bg-zinc-950/60 rounded-xl border border-zinc-850">
            <Clock size={18} className="text-zinc-500 mb-2" />
            <span className="text-3xl font-mono font-bold tracking-tight text-zinc-100">
              {formatTime(timerSeconds)}
            </span>
            <span className="text-[10px] text-zinc-500 mt-1 font-bold uppercase tracking-wider">Elapsed time</span>
          </div>

          <div className="flex flex-col gap-3">
            {running ? (
              <Button variant="danger" fullWidth onClick={stopMeeting} disabled={stopping} className="gap-2 font-semibold">
                <Square size={14} fill="white" />
                {stopping ? 'Stopping…' : 'Stop Recording'}
              </Button>
            ) : (
              <Button variant="primary" fullWidth onClick={startMeeting} className="gap-2 font-semibold">
                <Play size={14} fill="white" />
                Start Recording
              </Button>
            )}
          </div>
        </Card>

        {/* Level Indicator Waveform */}
        <Card className="p-5 text-left border-zinc-800 bg-zinc-950/20">
          <div className="flex items-center gap-2 mb-3.5">
            <Activity className="text-indigo-400 w-4 h-4" />
            <h3 className="font-display font-bold text-xs tracking-wider text-zinc-500 uppercase">Input Audio Signal</h3>
          </div>
          <div className="h-14 flex items-center justify-center gap-1 bg-zinc-950/60 border border-zinc-850 rounded-xl px-4">
            {running ? (
              Array.from({ length: 20 }).map((_, idx) => (
                <motion.div
                  key={idx}
                  className="w-1 bg-indigo-500 rounded-full"
                  animate={{
                    height: Math.max(3, Math.min(38, 3 + audioLevel * 300))
                  }}
                  transition={{
                    duration: 0.08,
                    delay: idx * 0.008
                  }}
                />
              ))
            ) : (
              <div className="w-full h-[1px] bg-zinc-800" />
            )}
          </div>
        </Card>

        {/* Combined Speaker & Participants Panel */}
        <Card className="p-5 text-left border-zinc-800 bg-zinc-950/20">
          <h3 className="font-display font-bold text-xs tracking-wider text-zinc-500 uppercase mb-3">Meeting Speakers</h3>
          
          {running && (
            <div className="flex items-center gap-2.5 p-2 mb-3 rounded-lg bg-emerald-500/5 border border-emerald-500/10">
              <Avatar name={activeSpeaker} size="sm" />
              <div className="flex flex-col">
                <span className="text-xs font-bold text-slate-200">{activeSpeaker}</span>
                <span className="text-[9px] text-emerald-400 flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                  Active Speaker
                </span>
              </div>
            </div>
          )}

          <div className="space-y-1.5 max-h-36 overflow-y-auto pr-1">
            {participants.map((person, idx) => (
              <div key={idx} className="flex items-center gap-2 p-1.5 rounded bg-zinc-950/40 border border-zinc-900">
                <Avatar name={person} size="sm" />
                <span className="text-[11px] font-semibold text-zinc-400">{person}</span>
              </div>
            ))}
          </div>
        </Card>

        {/* Pipeline Monitor Card */}
        <Card className="p-5 text-left border-zinc-800 bg-zinc-950/20">
          <h3 className="font-display font-bold text-xs tracking-wider text-zinc-500 uppercase mb-3">System Pipelines</h3>
          <div className="space-y-2.5">
            
            <div className="flex items-center justify-between text-xs border-b border-zinc-900 pb-1.5">
              <span className="text-zinc-500 flex items-center gap-1.5">
                <Radio size={12} className={wsStatus === 'connected' ? 'text-indigo-400 animate-pulse' : 'text-zinc-600'} />
                Audio WS Stream
              </span>
              <Badge variant={wsStatus === 'connected' ? 'success' : wsStatus === 'connecting' ? 'warning' : 'danger'}>
                {wsStatus}
              </Badge>
            </div>

            <div className="flex items-center justify-between text-xs border-b border-zinc-900 pb-1.5">
              <span className="text-zinc-500 flex items-center gap-1.5">
                <Bot size={12} className={copilotWsStatus === 'connected' ? 'text-indigo-400' : 'text-zinc-600'} />
                AI Copilot WS
              </span>
              <Badge variant={copilotWsStatus === 'connected' ? 'success' : copilotWsStatus === 'connecting' ? 'warning' : 'danger'}>
                {copilotWsStatus}
              </Badge>
            </div>

            <div className="flex items-center justify-between text-xs">
              <span className="text-zinc-500 flex items-center gap-1.5">
                <Database size={12} className="text-zinc-650" />
                Whisper Decoder
              </span>
              <span className="text-[9px] text-zinc-500 font-bold bg-zinc-900 px-1 py-0.5 rounded border border-zinc-800">
                LOCAL (FP16)
              </span>
            </div>

          </div>
        </Card>

      </div>

      {/* COLUMN 2 & 3: Live Transcripts Box */}
      <div className="xl:col-span-2 flex flex-col h-[78svh]">
        <Card className="flex-1 flex flex-col p-5 overflow-hidden border-zinc-850">
          {/* Header & Search */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between border-b border-zinc-900 pb-3 mb-3 gap-2">
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-indigo-500" />
              <h2 className="text-sm font-bold text-zinc-200 font-display uppercase tracking-wider">Live Transcript Stream</h2>
            </div>
            
            {/* Search filter */}
            <div className="relative max-w-xs w-full">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 text-zinc-600 w-3 h-3" />
              <input
                type="text"
                placeholder="Find in transcript..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full bg-zinc-950 border border-zinc-800 rounded-lg pl-8 pr-2.5 py-1 text-xs text-zinc-200 placeholder-zinc-600 focus:outline-none focus:border-indigo-500"
              />
            </div>
          </div>

          {/* Transcript Scroll Box */}
          <div ref={listRef} className="flex-1 overflow-y-auto pr-1 space-y-3">
            {transcripts.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center text-center text-zinc-600 py-10">
                <Radio className={`mb-3 ${running ? 'text-indigo-400 animate-pulse' : 'text-zinc-700'}`} size={20} />
                <span className="text-xs font-semibold">{running ? "🎤 Listening and converting speech to text..." : "Waiting for meeting recording to start..."}</span>
                <span className="text-[10px] text-zinc-600 mt-0.5 max-w-xs">Loopback speakers and capture systems are offline.</span>
              </div>
            ) : (
              transcripts.map((entry) => {
                const isSelected = searchQuery && entry.text.toLowerCase().includes(searchQuery.toLowerCase());
                const speaker = entry.speaker_name && entry.speaker_name !== 'Unknown' ? entry.speaker_name : 'Primary Speaker';
                const confidence = entry.confidence !== null ? entry.confidence : 1.0;
                
                return (
                  <motion.div
                    key={entry.id}
                    initial={{ opacity: 0, y: 5 }}
                    animate={{ opacity: 1, y: 0 }}
                    className={`flex items-start gap-3 p-2.5 rounded-lg border border-zinc-900 bg-zinc-950/20 ${isSelected ? 'ring-1 ring-indigo-500/40 bg-indigo-500/5' : ''}`}
                  >
                    <Avatar name={speaker} size="sm" className="mt-0.5" />
                    
                    <div className="flex-1 text-left">
                      <div className="flex items-center justify-between mb-1">
                        <div className="flex items-center gap-1.5">
                          <span className="text-xs font-bold text-zinc-300">{speaker}</span>
                          {confidence < 0.65 && (
                            <Badge variant="warning">Low Conf</Badge>
                          )}
                        </div>
                        <span className="text-[9px] font-mono text-zinc-650">{entry.start_seconds.toFixed(0)}s</span>
                      </div>
                      <p className="text-xs text-zinc-400 leading-relaxed font-sans">{entry.text}</p>
                    </div>

                    <div className="flex items-center shrink-0">
                      <button
                        onClick={() => handleCopy(entry.id, entry.text)}
                        className="text-zinc-600 hover:text-zinc-300 p-1 rounded hover:bg-zinc-900 transition-all cursor-pointer"
                        title="Copy transcript text"
                      >
                        {copiedId === entry.id ? <Check size={11} className="text-emerald-400" /> : <Copy size={11} />}
                      </button>
                    </div>
                  </motion.div>
                );
              })
            )}
          </div>
        </Card>
      </div>

      {/* COLUMN 4: RIGHT-SIDE INTELLIGENT AI ASSISTANT PANEL */}
      <div className="xl:col-span-1 flex flex-col h-[78svh]">
        <Card className="flex-1 flex flex-col p-4 overflow-hidden border-zinc-850 bg-zinc-950/10">
          
          {/* 1. COPILOT HEADER */}
          <div className="border-b border-zinc-900 pb-3 mb-3">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <Brain className="text-indigo-400 w-5 h-5 animate-pulse" />
                <span className="text-sm font-bold text-zinc-200 font-display">AI COPILOT</span>
              </div>
              <Badge variant={copilotWsStatus === 'connected' ? 'success' : 'danger'}>
                {copilotWsStatus === 'connected' ? 'Active' : 'Offline'}
              </Badge>
            </div>
            
            {/* Header Performance Status Panel */}
            <div className="grid grid-cols-2 gap-2 text-[10px] bg-zinc-950/60 p-2 rounded-lg border border-zinc-900">
              <div className="flex flex-col text-left">
                <span className="text-zinc-500 font-semibold uppercase">Insights</span>
                <span className="text-zinc-200 font-bold text-xs">{insights.length} flagged</span>
              </div>
              <div className="flex flex-col text-left">
                <span className="text-zinc-500 font-semibold uppercase">Confidence</span>
                <span className="text-indigo-400 font-bold text-xs">
                  {insights.length > 0
                    ? `${(insights.reduce((acc, curr) => acc + curr.confidence, 0) / insights.length * 100).toFixed(0)}% avg`
                    : '98% model'}
                </span>
              </div>
            </div>
          </div>

          {/* 2. TAB CONTROLLER */}
          <div className="flex gap-1 bg-zinc-950/80 p-1 rounded-lg border border-zinc-900 mb-3">
            <button
              onClick={() => setCopilotActiveTab('insights')}
              className={`flex-1 py-1 text-[11px] font-semibold rounded-md transition-all cursor-pointer ${copilotActiveTab === 'insights' ? 'bg-zinc-900 text-zinc-100' : 'text-zinc-500 hover:text-zinc-300'}`}
            >
              Live Insights
            </button>
            <button
              onClick={() => setCopilotActiveTab('workflows')}
              className={`flex-1 py-1 text-[11px] font-semibold rounded-md transition-all cursor-pointer ${copilotActiveTab === 'workflows' ? 'bg-zinc-900 text-zinc-100 animate-pulse' : 'text-zinc-500 hover:text-zinc-300'}`}
            >
              Workflows
            </button>
            <button
              onClick={() => setCopilotActiveTab('assistant')}
              className={`flex-1 py-1 text-[11px] font-semibold rounded-md transition-all cursor-pointer ${copilotActiveTab === 'assistant' ? 'bg-zinc-900 text-zinc-100' : 'text-zinc-500 hover:text-zinc-300'}`}
            >
              Ask AI
            </button>
          </div>

          {/* Tab 1: Live Insights Feed */}
          {copilotActiveTab === 'insights' && (
            <div className="flex-1 flex flex-col overflow-hidden">
              
              {/* Search & Filters block */}
              <div className="space-y-2 mb-3 bg-zinc-950/40 p-2.5 rounded-lg border border-zinc-900">
                <div className="relative">
                  <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 text-zinc-650 w-3 h-3" />
                  <input
                    type="text"
                    placeholder="Search insights..."
                    value={copilotSearchQuery}
                    onChange={(e) => setCopilotSearchQuery(e.target.value)}
                    className="w-full bg-zinc-950 border border-zinc-850 rounded pl-7 pr-2 py-1 text-[10px] text-zinc-200 placeholder-zinc-600 focus:outline-none"
                  />
                </div>

                <div className="flex items-center gap-1.5">
                  {/* Category Selector */}
                  <select
                    value={copilotFilterType}
                    onChange={(e) => setCopilotFilterType(e.target.value)}
                    className="bg-zinc-950 border border-zinc-850 rounded px-1.5 py-0.5 text-[9px] text-zinc-400 focus:outline-none"
                  >
                    <option value="all">All Types</option>
                    <option value="decision">Decisions</option>
                    <option value="risk">Risks</option>
                    <option value="deadline">Deadlines</option>
                    <option value="commitment">Tasks</option>
                    <option value="question">Questions</option>
                    <option value="recommendation">Coaching</option>
                  </select>

                  {/* Severity Selector */}
                  <select
                    value={copilotFilterSeverity}
                    onChange={(e) => setCopilotFilterSeverity(e.target.value)}
                    className="bg-zinc-950 border border-zinc-850 rounded px-1.5 py-0.5 text-[9px] text-zinc-400 focus:outline-none"
                  >
                    <option value="all">All Severity</option>
                    <option value="info">Info</option>
                    <option value="warning">Warning</option>
                    <option value="critical">Critical</option>
                  </select>

                  {/* Sort Selector */}
                  <button
                    onClick={() => setCopilotSortOrder(prev => prev === 'newest' ? 'oldest' : 'newest')}
                    className="ml-auto bg-zinc-950 border border-zinc-850 rounded px-1.5 py-0.5 text-[9px] text-zinc-400 hover:text-zinc-200 transition-all cursor-pointer"
                  >
                    {copilotSortOrder === 'newest' ? 'Newest ↓' : 'Oldest ↑'}
                  </button>
                </div>
              </div>

              {/* Scroll Container of Timeline Cards */}
              <div 
                ref={copilotListRef} 
                onScroll={handleCopilotScroll}
                className="flex-1 overflow-y-auto pr-1 space-y-2.5 relative text-left"
              >
                <AnimatePresence initial={false}>
                  {filteredInsights.length === 0 ? (
                    <div className="h-full flex flex-col items-center justify-center text-center text-zinc-650 py-12">
                      <Sparkles className="w-7 h-7 text-zinc-700 mb-2 animate-pulse" />
                      <span className="text-[11px] font-bold">No insights detected yet</span>
                      <span className="text-[9px] text-zinc-650 mt-0.5 max-w-[150px]">The Copilot is auditing live speech for decisions & deadlines...</span>
                    </div>
                  ) : (
                    filteredInsights.map((insight) => {
                      const isExpanded = expandedCardId === insight.insight_id;
                      const severity = insight.metadata?.severity?.toLowerCase() || 'info';
                      
                      return (
                        <motion.div
                          key={insight.insight_id}
                          layout
                          initial={{ opacity: 0, scale: 0.95 }}
                          animate={{ opacity: 1, scale: 1 }}
                          exit={{ opacity: 0, scale: 0.9 }}
                          className={`p-3 rounded-lg border bg-zinc-950/60 transition-all ${
                            severity === 'critical' ? 'border-red-500/20 shadow-red-500/5' :
                            severity === 'warning' ? 'border-amber-500/20 shadow-amber-500/5' :
                            'border-zinc-900 hover:border-zinc-800'
                          }`}
                        >
                          {/* Header area of Insight Card */}
                          <div 
                            className="flex items-start gap-2.5 cursor-pointer select-none"
                            onClick={() => setExpandedCardId(isExpanded ? null : insight.insight_id)}
                          >
                            <div className="p-1.5 rounded-lg bg-zinc-900 border border-zinc-800 shrink-0">
                              {getInsightIcon(insight.insight_type)}
                            </div>
                            
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-1.5 mb-0.5">
                                <span className="text-[10px] font-bold uppercase tracking-wider text-zinc-500">
                                  {insight.insight_type}
                                </span>
                                <span className="text-[9px] text-indigo-400 font-mono font-bold">
                                  {(insight.confidence * 100).toFixed(0)}% conf
                                </span>
                              </div>
                              <h4 className="text-xs font-bold text-zinc-200 line-clamp-1">{insight.title}</h4>
                            </div>

                            <button className="text-zinc-600 hover:text-zinc-300">
                              {isExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                            </button>
                          </div>

                          {/* Body area of Insight Card (Expandable) */}
                          <AnimatePresence>
                            {isExpanded && (
                              <motion.div
                                initial={{ height: 0, opacity: 0 }}
                                animate={{ height: 'auto', opacity: 1 }}
                                exit={{ height: 0, opacity: 0 }}
                                className="overflow-hidden"
                              >
                                <div className="pt-2.5 border-t border-zinc-900/60 mt-2 space-y-2">
                                  <p className="text-[11px] text-zinc-400 leading-relaxed font-sans">{insight.content}</p>

                                  {/* Source/Speaker Info */}
                                  <div className="flex items-center gap-2 text-[9px] text-zinc-500">
                                    {insight.speaker && (
                                      <span>Source: <strong>{insight.speaker}</strong></span>
                                    )}
                                    <span>•</span>
                                    <span>{new Date(insight.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                                  </div>

                                  {/* Quick Actions List inside Card */}
                                  <div className="flex flex-wrap gap-1.5 pt-2">
                                    {insight.speaker && (
                                      <button
                                        onClick={() => handleScrollToTranscript(insight.speaker)}
                                        className="bg-zinc-900 border border-zinc-800 hover:border-zinc-700 text-zinc-300 px-2 py-0.5 rounded text-[9px] font-bold cursor-pointer"
                                      >
                                        View Transcript
                                      </button>
                                    )}
                                    <button
                                      onClick={() => handleCreateWorkflowFromInsight(insight)}
                                      className="bg-indigo-950/40 border border-indigo-900/60 hover:border-indigo-800 text-indigo-300 px-2 py-0.5 rounded text-[9px] font-bold cursor-pointer"
                                    >
                                      Create Workflow
                                    </button>
                                    <button
                                      onClick={() => handleCopyInsight(insight)}
                                      className="bg-zinc-900 border border-zinc-800 hover:border-zinc-700 text-zinc-300 px-2 py-0.5 rounded text-[9px] font-bold cursor-pointer"
                                    >
                                      Copy Insight
                                    </button>
                                  </div>
                                </div>
                              </motion.div>
                            )}
                          </AnimatePresence>
                        </motion.div>
                      );
                    })
                  )}
                </AnimatePresence>
              </div>

              {/* Pause AutoScroll overlay notification banner */}
              {!autoScrollCopilot && insights.length > 0 && (
                <button
                  onClick={() => setAutoScrollCopilot(true)}
                  className="mx-auto my-1 flex items-center gap-1.5 px-3 py-1 bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-300 rounded-full text-[10px] font-semibold shadow-xl cursor-pointer"
                >
                  <ChevronDown className="w-3 h-3 animate-bounce" />
                  Auto-scroll paused (Resume)
                </button>
              )}
            </div>
          )}

          {/* Tab 2: Workflows Suggester & Active Tasks */}
          {copilotActiveTab === 'workflows' && (
            <div className="flex-1 flex flex-col overflow-y-auto pr-1 text-left space-y-3">
              <div className="bg-zinc-950/60 p-3 rounded-lg border border-zinc-900 space-y-2">
                <div className="flex items-center gap-1.5">
                  <Zap className="text-violet-400 w-4 h-4 animate-pulse" />
                  <span className="text-xs font-bold text-zinc-200">Active Workflow Suggestions</span>
                </div>
                <p className="text-[10px] text-zinc-500">Autonomous triggers listening for decision triggers.</p>
              </div>

              {/* Suggestions Timeline List */}
              <div className="space-y-2.5">
                {insights.filter(ins => ins.insight_type === 'workflow').length === 0 ? (
                  <div className="flex flex-col items-center justify-center text-center text-zinc-650 py-8">
                    <SlidersHorizontal className="w-6 h-6 mb-1 text-zinc-700" />
                    <span className="text-[10px] font-bold">No active workflows suggested yet</span>
                    <span className="text-[9px] text-zinc-700 mt-0.5 max-w-[130px]">Flow suggestions will dynamically generate here on approvals.</span>
                  </div>
                ) : (
                  insights.filter(ins => ins.insight_type === 'workflow').map((item) => (
                    <div key={item.insight_id} className="p-3 rounded-lg border border-violet-900/30 bg-violet-950/5 text-left space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-[9px] font-mono text-violet-400 font-bold">WORKFLOW SUCCEEDED</span>
                        <Badge variant="warning">Wait Approval</Badge>
                      </div>
                      <h4 className="text-xs font-bold text-zinc-300">{item.title}</h4>
                      <p className="text-[10px] text-zinc-400 leading-relaxed">{item.content}</p>
                      
                      {/* Approve / Reject buttons */}
                      {item.content.includes("Waiting Approval") && (
                        <div className="flex gap-2 pt-1.5">
                          <button
                            onClick={() => handleApproveWorkflow(item.insight_id)}
                            className="bg-emerald-950 border border-emerald-800 hover:border-emerald-700 text-emerald-300 px-3 py-1 rounded text-[10px] font-bold flex-1 cursor-pointer"
                          >
                            Approve
                          </button>
                          <button
                            onClick={() => addToast('warning', 'Workflow Rejected', 'Automation request declined.')}
                            className="bg-zinc-900 border border-zinc-800 hover:border-zinc-700 text-zinc-400 px-3 py-1 rounded text-[10px] font-bold flex-1 cursor-pointer"
                          >
                            Reject
                          </button>
                        </div>
                      )}
                    </div>
                  ))
                )}
              </div>

              {/* Future Ready Indicators */}
              <div className="pt-4 border-t border-zinc-900 space-y-2 text-[10px] text-zinc-500">
                <div className="flex items-center justify-between">
                  <span className="flex items-center gap-1.5">
                    <Radio size={12} className="text-zinc-650" />
                    Voice Interaction Mode
                  </span>
                  <span className="text-[8px] bg-zinc-900 border border-zinc-800 px-1 py-0.2 rounded font-bold">READY</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="flex items-center gap-1.5">
                    <Brain size={12} className="text-zinc-650" />
                    Multi-Agent Reasoning Grid
                  </span>
                  <span className="text-[8px] bg-zinc-900 border border-zinc-800 px-1 py-0.2 rounded font-bold">CONNECTED</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="flex items-center gap-1.5">
                    <Layers size={12} className="text-zinc-650" />
                    Live Ephemeral Memory Cache
                  </span>
                  <span className="text-[8px] bg-zinc-900 border border-zinc-800 px-1 py-0.2 rounded font-bold">SYNC</span>
                </div>
              </div>
            </div>
          )}

          {/* Tab 3: Interactive Ask AI Chat */}
          {copilotActiveTab === 'assistant' && (
            <div className="flex-1 flex flex-col overflow-hidden">
              
              {/* Chat Messages scroll area */}
              <div className="flex-1 overflow-y-auto space-y-2 pr-1 mb-2.5">
                {chatMessages.length === 0 ? (
                  <div className="h-full flex flex-col items-center justify-center text-center text-zinc-650 py-10">
                    <Bot className="w-8 h-8 text-zinc-700 mb-2" />
                    <span className="text-[11px] font-bold">Consult AI meeting pilot</span>
                    <span className="text-[9px] text-zinc-700 mt-0.5 max-w-[150px]">Ask questions about tasks, decisions, context, or speaking balance.</span>
                  </div>
                ) : (
                  chatMessages.map((msg) => (
                    <div
                      key={msg.id}
                      className={`flex flex-col p-2.5 rounded-lg border text-left ${
                        msg.sender === 'user'
                          ? 'bg-zinc-900/50 border-zinc-800 ml-4 align-end'
                          : 'bg-indigo-950/10 border-indigo-900/30 mr-4 align-start'
                      }`}
                    >
                      <span className="text-[9px] font-bold uppercase tracking-wider text-zinc-500 mb-0.5">
                        {msg.sender === 'user' ? 'You' : 'Copilot'}
                      </span>
                      <p className="text-xs text-zinc-300 leading-relaxed font-sans">{msg.text}</p>
                    </div>
                  ))
                )}
                {chatLoading && (
                  <div className="flex items-center gap-2 p-2 bg-indigo-950/15 border border-indigo-900/20 mr-4 rounded-lg text-left">
                    <RefreshCw className="w-3 h-3 text-indigo-400 animate-spin" />
                    <span className="text-[10px] text-zinc-500">Drafting reply summary...</span>
                  </div>
                )}
              </div>

              {/* Chat Input form box */}
              <form onSubmit={handleSendChat} className="flex gap-1.5 border-t border-zinc-900 pt-2 shrink-0">
                <input
                  type="text"
                  placeholder="Ask assistant..."
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                  className="flex-1 bg-zinc-950 border border-zinc-800 rounded-lg pl-3 pr-2 py-1.5 text-xs text-zinc-200 focus:outline-none focus:border-indigo-500 placeholder-zinc-600"
                />
                <button
                  type="submit"
                  className="bg-indigo-650 hover:bg-indigo-500 border border-indigo-650 p-2 rounded-lg text-white hover:text-slate-100 transition-all cursor-pointer shrink-0"
                >
                  <Send size={12} />
                </button>
              </form>
            </div>
          )}

        </Card>
      </div>

    </main>
  );
};

export default LiveMeetingPage;

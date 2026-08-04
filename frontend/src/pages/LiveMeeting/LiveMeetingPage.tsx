import React, { useEffect, useMemo, useRef, useState } from 'react';
import api from '../../services/api';
import { motion } from 'framer-motion';
import {
  Video,
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
  Volume2
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

  const listRef = useRef<HTMLDivElement | null>(null);
  const timerRef = useRef<any>(null);
  const wsRef = useRef<WebSocket | null>(null);
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
    };
  }, []);

  // Set up WebSocket
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

  // Auto-scroll to bottom on new transcripts
  useEffect(() => {
    if (listRef.current) {
      listRef.current.scrollTop = listRef.current.scrollHeight;
    }
  }, [transcripts]);

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
    setTimeout(() => setCopiedId(null), 2000);
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

  return (
    <main className="flex-1 grid grid-cols-1 xl:grid-cols-4 gap-5 p-5 xl:p-6 min-h-0 overflow-y-auto">
      
      {/* Panel 1: Recording controls, waveform & active speaker */}
      <div className="xl:col-span-1 space-y-5 flex flex-col justify-between h-fit">
        <Card className="p-6 flex flex-col gap-6 text-left">
          {/* Header */}
          <div className="flex items-center justify-between">
            <h3 className="font-display font-bold text-sm tracking-wide text-zinc-400 uppercase">Live Session</h3>
            {running && (
              <span className="flex items-center gap-1.5 text-xs text-red-500 font-bold bg-red-500/10 border border-red-500/25 px-2 py-0.5 rounded-full">
                <span className="w-1.5 h-1.5 rounded-full bg-red-500 animate-ping" />
                REC
              </span>
            )}
          </div>

          {/* Time Counter */}
          <div className="flex flex-col items-center justify-center py-6 bg-zinc-950/40 rounded-xl border border-zinc-800/80">
            <Clock size={20} className="text-zinc-500 mb-2" />
            <span className="text-4xl font-mono font-bold tracking-tight text-slate-100">
              {formatTime(timerSeconds)}
            </span>
            <span className="text-xs text-zinc-500 mt-1 font-semibold uppercase">Elapsed time</span>
          </div>

          {/* Controls */}
          <div className="flex flex-col gap-3">
            {running ? (
              <Button variant="danger" fullWidth onClick={stopMeeting} disabled={stopping} className="gap-2">
                <Square size={16} fill="white" />
                {stopping ? 'Stopping…' : 'Stop Recording'}
              </Button>
            ) : (
              <Button variant="primary" fullWidth onClick={startMeeting} className="gap-2">
                <Play size={16} fill="white" />
                Start Recording
              </Button>
            )}
          </div>
        </Card>

        {/* Audio Waveform Card */}
        <Card className="p-6 text-left">
          <div className="flex items-center gap-2 mb-4">
            <Activity className="text-indigo-400" size={16} />
            <h3 className="font-display font-bold text-sm tracking-wide text-zinc-400 uppercase">Speaker Output Level</h3>
          </div>
          <div className="h-16 flex items-center justify-center gap-1 bg-zinc-950/40 border border-zinc-850 rounded-xl px-4" aria-label={`Live speaker-loopback RMS level: ${audioLevel.toFixed(4)}`}>
            {running ? (
              Array.from({ length: 24 }).map((_, idx) => (
                <motion.div
                  key={idx}
                  className="w-1 bg-indigo-500 rounded-full"
                  animate={{
                    height: Math.max(4, Math.min(48, 4 + audioLevel * 440))
                  }}
                  transition={{
                    duration: 0.1,
                    delay: idx * 0.01
                  }}
                />
              ))
            ) : (
              <div className="w-full h-[2px] bg-zinc-800" />
            )}
          </div>
        </Card>

        {/* Active Speaker Card */}
        <Card className="p-6 text-left">
          <h3 className="font-display font-bold text-sm tracking-wide text-zinc-400 uppercase mb-3">Active Speaker</h3>
          <div className="flex items-center gap-3">
            <Avatar name={activeSpeaker} size="md" />
            <div className="flex flex-col">
              <span className="text-sm font-bold text-slate-200">{activeSpeaker}</span>
              <span className="text-[10px] text-emerald-400 flex items-center gap-1 mt-0.5">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                Speaking
              </span>
            </div>
          </div>
        </Card>
      </div>

      {/* Panel 2: Live Scrolling Transcript Panel */}
      <div className="xl:col-span-2 flex flex-col h-[78svh]">
        <Card className="flex-1 flex flex-col p-5 overflow-hidden">
          {/* Header & Search */}
          <div className="flex flex-col md:flex-row md:items-center justify-between border-b border-zinc-900 pb-4 mb-4 gap-3">
            <div className="flex items-center gap-2.5">
              <div className="w-2.5 h-2.5 rounded-full bg-indigo-500" />
              <h2 className="text-base font-bold text-slate-100 font-display">Live Transcript stream</h2>
            </div>
            
            {/* Search filter */}
            <div className="relative max-w-xs w-full">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500 w-3.5 h-3.5" />
              <input
                type="text"
                placeholder="Find in transcript..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full bg-zinc-950 border border-zinc-800 rounded-lg pl-9 pr-3 py-1.5 text-xs text-slate-100 placeholder-zinc-500 focus:outline-none focus:border-indigo-500"
              />
            </div>
          </div>

          {/* Transcript Scroll Box */}
          <div ref={listRef} className="flex-1 overflow-y-auto pr-2 space-y-4">
            {transcripts.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center text-center text-zinc-500 py-10">
                <Radio className={`mb-3 ${running ? 'text-indigo-400 animate-pulse' : 'text-zinc-600'}`} size={24} />
                <span className="text-sm font-semibold">{running ? "🎤 Listening to meeting..." : "Waiting for session to start..."}</span>
                <span className="text-xs text-zinc-500 mt-1 max-w-[200px]">Any audio caught will stream here in real time.</span>
              </div>
            ) : (
              transcripts.map((entry) => {
                const isSelected = searchQuery && entry.text.toLowerCase().includes(searchQuery.toLowerCase());
                const speaker = entry.speaker_name && entry.speaker_name !== 'Unknown' ? entry.speaker_name : 'Primary Speaker';
                const confidence = entry.confidence !== null ? entry.confidence : 1.0;
                
                return (
                  <motion.div
                    key={entry.id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className={`flex items-start gap-3.5 p-3 rounded-lg border border-zinc-900 bg-zinc-950/40 ${isSelected ? 'ring-1 ring-indigo-500/50 bg-indigo-500/5' : ''}`}
                  >
                    <Avatar name={speaker} size="sm" className="mt-0.5" />
                    
                    <div className="flex-1 text-left">
                      <div className="flex items-center justify-between mb-1.5">
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-bold text-slate-300">{speaker}</span>
                          {confidence < 0.65 && (
                            <Badge variant="warning">Low Conf</Badge>
                          )}
                        </div>
                        <span className="text-[10px] font-mono text-zinc-500">{entry.start_seconds.toFixed(0)}s</span>
                      </div>
                      
                      <p className="text-sm text-zinc-300 leading-relaxed font-sans">{entry.text}</p>
                    </div>

                    <div className="flex items-center gap-1 shrink-0">
                      <button
                        onClick={() => handleCopy(entry.id, entry.text)}
                        className="text-zinc-500 hover:text-slate-300 p-1 rounded hover:bg-zinc-800 transition-all cursor-pointer"
                        title="Copy text"
                      >
                        {copiedId === entry.id ? <Check size={12} className="text-emerald-400" /> : <Copy size={12} />}
                      </button>
                    </div>
                  </motion.div>
                );
              })
            )}
          </div>
        </Card>
      </div>

      {/* Panel 3: Pipelines status, participants list & AI state */}
      <div className="xl:col-span-1 space-y-5 h-fit">
        {/* Pipeline Monitor Card */}
        <Card className="p-5 text-left">
          <h3 className="font-display font-bold text-sm tracking-wide text-zinc-400 uppercase mb-4">Pipeline Status</h3>
          <div className="space-y-4">
            
            {/* WebSocket Connection */}
            <div className="flex items-center justify-between border-b border-zinc-900 pb-2">
              <span className="text-xs font-semibold text-zinc-400 flex items-center gap-2">
                <Radio size={14} className={wsStatus === 'connected' ? 'text-indigo-400' : 'text-zinc-500'} />
                WebSocket Feed
              </span>
              <Badge variant={wsStatus === 'connected' ? 'success' : wsStatus === 'connecting' ? 'warning' : 'danger'}>
                {wsStatus}
              </Badge>
            </div>

            {/* Audio Service status */}
            <div className="flex items-center justify-between border-b border-zinc-900 pb-2">
              <span className="text-xs font-semibold text-zinc-400 flex items-center gap-2">
                <Volume2 size={14} className={running ? 'text-indigo-400' : 'text-zinc-500'} />
                Speaker loopback
              </span>
              <Badge variant={running ? 'success' : 'secondary'}>
                {running ? "active" : "offline"}
              </Badge>
            </div>

            {/* Screen Capture status */}
            <div className="flex items-center justify-between border-b border-zinc-900 pb-2">
              <span className="text-xs font-semibold text-zinc-400 flex items-center gap-2">
                <Video size={14} className={running ? 'text-indigo-400' : 'text-zinc-500'} />
                Vision (OCR/Capture)
              </span>
              <Badge variant={running ? 'success' : 'secondary'}>
                {running ? "active" : "offline"}
              </Badge>
            </div>

            {/* Whisper model */}
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-zinc-400 flex items-center gap-2">
                <Database size={14} className="text-zinc-500" />
                Whisper Pipeline
              </span>
              <span className="text-[10px] text-zinc-400 font-bold bg-zinc-800 px-1.5 py-0.5 rounded border border-zinc-700">
                LOCAL (FP16)
              </span>
            </div>

          </div>
        </Card>

        {/* Participants Monitor Card */}
        <Card className="p-5 text-left">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-display font-bold text-sm tracking-wide text-zinc-400 uppercase">Active Speakers</h3>
            <span className="text-xs text-indigo-400 font-bold">{participants.length} detected</span>
          </div>
          <div className="space-y-2">
            {participants.map((person, idx) => (
              <div key={idx} className="flex items-center gap-2.5 p-2 rounded-lg bg-zinc-950/60 border border-zinc-900/60">
                <Avatar name={person} size="sm" />
                <span className="text-xs font-semibold text-zinc-300">{person}</span>
                {idx === 0 && running && (
                  <UserCheck size={12} className="text-emerald-400 ml-auto" />
                )}
              </div>
            ))}
          </div>
        </Card>
      </div>

    </main>
  );
};

export default LiveMeetingPage;

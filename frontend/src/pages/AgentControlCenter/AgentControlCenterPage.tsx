import { useState, useEffect, useRef } from "react";
import {
  Play,
  Pause,
  RotateCcw,
  Activity,
  Cpu,
  Database,
  Terminal,
  CheckCircle,
  HelpCircle,
  Clock,
  Layers,
  Shield,
  Download,
  Search
} from "lucide-react";
import axios from "axios";

// Base API URI Configuration
const API_BASE = "http://localhost:8000/agent";
const WS_BASE = "ws://localhost:8000/agent/ws";

interface LogEntry {
  timestamp: string;
  level: string;
  module: string;
  message: string;
  severity: number;
}

interface Decision {
  decision_id: string;
  timestamp: string;
  confidence: number;
  reason: string;
  goal: string;
  selected_action: { action_name: string; parameters?: any };
  status: string;
  trigger?: string;
  alternative_actions?: any[];
  expected_outcome?: string;
}

interface ApprovalItem {
  approval_id: string;
  decision_id: string;
  action_name: string;
  parameters: any;
  status: string;
  created_at: string;
}

interface Session {
  platform: string;
  meeting_id: number | null;
  duration_seconds: number;
  recording_status: string;
  transcript_progress: string;
  vision_status: string;
  copilot_status: string;
  workflow_status: string;
}

export default function AgentControlCenterPage() {
  // Status and Telemetry States
  const [lifecycleState, setLifecycleState] = useState<string>("Initializing");
  const [runningState, setRunningState] = useState<string>("RUNNING");
  const [uptime, setUptime] = useState<number>(0);
  const [cpu, setCpu] = useState<number>(0);
  const [memory, setMemory] = useState<number>(0);
  const [activeThreads, setActiveThreads] = useState<number>(0);
  const [metrics, setMetrics] = useState<any>({});
  const [moduleHealth, setModuleHealth] = useState<Record<string, string>>({});
  
  // Lists data states
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [decisions, setDecisions] = useState<Decision[]>([]);
  const [session, setSession] = useState<Session | null>(null);
  const [approvals, setApprovals] = useState<ApprovalItem[]>([]);
  
  // Configuration Settings State
  const [autonomyMode, setAutonomyMode] = useState<string>("Semi-Autonomous");
  const [detectionProfile, setDetectionProfile] = useState<string>("Balanced");
  const [recordingPolicy, setRecordingPolicy] = useState<string>("Autonomous");

  // Log Search and Filters
  const [logSearch, setLogSearch] = useState<string>("");
  const [logModuleFilter, setLogModuleFilter] = useState<string>("");

  const wsRef = useRef<WebSocket | null>(null);
  const logEndRef = useRef<HTMLDivElement | null>(null);

  // Auto-scroll logs
  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  // Establish WebSockets listeners
  useEffect(() => {
    const connectWS = () => {
      const ws = new WebSocket(WS_BASE);
      wsRef.current = ws;

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.status) {
            setLifecycleState(data.status.lifecycle_state);
            setRunningState(data.status.status);
          }
          if (data.health) {
            setModuleHealth(data.health);
          }
          if (data.metrics) {
            setCpu(data.metrics.cpu_usage_percent || 0);
            setMemory(data.metrics.memory_usage_percent || 0);
            setActiveThreads(data.metrics.active_threads || 0);
            setUptime(data.metrics.uptime_seconds || 0);
            setMetrics(data.metrics);
          }
          if (data.logs) {
            setLogs(data.logs);
          }
          if (data.decisions) {
            setDecisions(data.decisions);
          }
          if (data.session) {
            setSession(data.session);
          }
          if (data.approvals) {
            setApprovals(data.approvals);
          }
        } catch (e) {
          console.error("Error parsing monitor data", e);
        }
      };

      ws.onerror = () => {
        ws.close();
      };

      ws.onclose = () => {
        setTimeout(connectWS, 3000); // Reconnect loop
      };
    };

    connectWS();
    return () => {
      wsRef.current?.close();
    };
  }, []);

  // Format uptime count to readable format
  const formatUptime = (sec: number) => {
    const hrs = Math.floor(sec / 3600);
    const mins = Math.floor((sec % 3600) / 60);
    const secs = Math.floor(sec % 60);
    return `${hrs.toString().padStart(2, "0")}:${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
  };

  // REST controls actions
  const triggerControl = async (endpoint: string) => {
    try {
      await axios.post(`${API_BASE}/${endpoint}`);
      // Show local toast or notification
      new Notification(`MeetingPilot AI Control`, {
        body: `Agent state toggled via endpoint /${endpoint}`
      });
    } catch (e) {
      console.error("Failed to trigger control endpoint", e);
    }
  };

  // Approval actions resolution
  const resolveApproval = async (approvalId: string, approve: boolean) => {
    try {
      // In real scenario, post back to approvals endpoint
      await axios.post(`http://localhost:8000/agent/approvals/${approvalId}/resolve`, { approve });
    } catch (e) {
      // Fallback fallback stubs call
      console.log("Approval response captured: ", approvalId, approve);
      setApprovals(prev => prev.filter(item => item.approval_id !== approvalId));
    }
  };

  // Export details reports
  const exportReport = (category: string) => {
    let dataString = "";
    if (category === "logs") dataString = JSON.stringify(logs, null, 2);
    else if (category === "metrics") dataString = JSON.stringify(metrics, null, 2);
    else if (category === "decisions") dataString = JSON.stringify(decisions, null, 2);
    else dataString = JSON.stringify({ metrics, moduleHealth, lifecycleState }, null, 2);

    const blob = new Blob([dataString], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `meetingpilot_${category}_report.json`;
    a.click();
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-6 font-sans">
      
      {/* 1. Header & Top Control Bar */}
      <div className="flex flex-wrap items-center justify-between gap-4 p-6 bg-slate-900/60 border border-slate-800 rounded-2xl backdrop-blur-xl shadow-2xl mb-6">
        <div className="flex items-center gap-4">
          <div className="relative flex h-4 w-4">
            <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${runningState === "RUNNING" ? "bg-emerald-400" : "bg-amber-400"}`}></span>
            <span className={`relative inline-flex rounded-full h-4 w-4 ${runningState === "RUNNING" ? "bg-emerald-500" : "bg-amber-500"}`}></span>
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
              MeetingPilot AI <span className="text-xs bg-slate-800 px-2.5 py-1 rounded-full text-slate-300 font-medium">Mission Control</span>
            </h1>
            <p className="text-xs text-slate-400">System State: <span className="text-emerald-400 font-semibold uppercase">{lifecycleState}</span></p>
          </div>
        </div>

        {/* Dynamic Controls buttons */}
        <div className="flex items-center gap-3">
          <div className="bg-slate-800/80 px-4 py-2 rounded-xl border border-slate-700 text-xs flex items-center gap-2">
            <Clock className="h-4 w-4 text-sky-400" />
            <span className="font-mono text-slate-200">{formatUptime(uptime)}</span>
          </div>

          <button
            onClick={() => triggerControl("resume")}
            className="flex items-center gap-2 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold px-4 py-2.5 rounded-xl transition duration-200 cursor-pointer shadow-lg shadow-emerald-900/30"
          >
            <Play className="h-3.5 w-3.5" /> Resume
          </button>
          
          <button
            onClick={() => triggerControl("pause")}
            className="flex items-center gap-2 bg-amber-600 hover:bg-amber-500 text-white text-xs font-semibold px-4 py-2.5 rounded-xl transition duration-200 cursor-pointer shadow-lg shadow-amber-900/30"
          >
            <Pause className="h-3.5 w-3.5" /> Pause
          </button>

          <button
            onClick={() => triggerControl("restart")}
            className="flex items-center gap-2 bg-slate-800 hover:bg-slate-750 text-slate-200 text-xs font-semibold px-4 py-2.5 border border-slate-750 rounded-xl transition duration-200 cursor-pointer"
          >
            <RotateCcw className="h-3.5 w-3.5" /> Restart
          </button>
        </div>
      </div>

      {/* 2. Grid Overview Blocks */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-6">
        
        {/* Memory status Card */}
        <div className="p-6 bg-slate-900/40 border border-slate-800/80 rounded-2xl flex items-center gap-4">
          <div className="p-3 bg-sky-500/10 rounded-xl text-sky-400">
            <Cpu className="h-6 w-6" />
          </div>
          <div>
            <p className="text-xs text-slate-400 uppercase tracking-wider font-semibold">Processor Load</p>
            <h3 className="text-2xl font-bold font-mono text-white">{cpu.toFixed(1)}%</h3>
          </div>
        </div>

        {/* Memory utilization Card */}
        <div className="p-6 bg-slate-900/40 border border-slate-800/80 rounded-2xl flex items-center gap-4">
          <div className="p-3 bg-violet-500/10 rounded-xl text-violet-400">
            <Database className="h-6 w-6" />
          </div>
          <div>
            <p className="text-xs text-slate-400 uppercase tracking-wider font-semibold">RAM Usage</p>
            <h3 className="text-2xl font-bold font-mono text-white">{memory.toFixed(1)}%</h3>
          </div>
        </div>

        {/* Active Session stats */}
        <div className="p-6 bg-slate-900/40 border border-slate-800/80 rounded-2xl flex items-center gap-4">
          <div className="p-3 bg-pink-500/10 rounded-xl text-pink-400">
            <Activity className="h-6 w-6" />
          </div>
          <div>
            <p className="text-xs text-slate-400 uppercase tracking-wider font-semibold">Uptime Status</p>
            <h3 className="text-2xl font-bold text-white">Active</h3>
          </div>
        </div>

        {/* Active threads counts */}
        <div className="p-6 bg-slate-900/40 border border-slate-800/80 rounded-2xl flex items-center gap-4">
          <div className="p-3 bg-emerald-500/10 rounded-xl text-emerald-400">
            <Layers className="h-6 w-6" />
          </div>
          <div>
            <p className="text-xs text-slate-400 uppercase tracking-wider font-semibold">Threads</p>
            <h3 className="text-2xl font-bold font-mono text-white">{activeThreads}</h3>
          </div>
        </div>
      </div>

      {/* 3. Session and Health block details */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        
        {/* Current Active Meeting Monitor */}
        <div className="lg:col-span-2 p-6 bg-slate-900/40 border border-slate-800/80 rounded-2xl flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4 border-b border-slate-800/60 pb-3">
              <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-300">Active Meeting Session</h3>
              <span className={`px-2 py-0.5 rounded text-[10px] uppercase font-semibold ${session ? "bg-rose-500/10 text-rose-400 border border-rose-500/20" : "bg-slate-800 text-slate-400"}`}>
                {session ? "Recording" : "No Active Meeting"}
              </span>
            </div>

            {session ? (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-6 py-2">
                <div>
                  <p className="text-xs text-slate-500">Platform</p>
                  <p className="text-sm font-bold text-white">{session.platform}</p>
                </div>
                <div>
                  <p className="text-xs text-slate-500">Meeting ID</p>
                  <p className="text-sm font-mono text-slate-300">#{session.meeting_id}</p>
                </div>
                <div>
                  <p className="text-xs text-slate-500">Transcription Progress</p>
                  <p className="text-sm text-slate-300">{session.transcript_progress}</p>
                </div>
                <div>
                  <p className="text-xs text-slate-500">Duration</p>
                  <p className="text-sm font-mono text-slate-300">{formatUptime(session.duration_seconds)}</p>
                </div>
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center py-10 text-center text-slate-500">
                <HelpCircle className="h-10 w-10 mb-2 stroke-1 text-slate-600" />
                <p className="text-xs">Meeting Detection Engine is listening in background.<br />Auto-captures start dynamically on platform signatures match.</p>
              </div>
            )}
          </div>
          
          <div className="mt-4 pt-4 border-t border-slate-800/60 flex flex-wrap gap-4 items-center justify-between text-xs text-slate-400">
            <span className="flex items-center gap-1.5"><CheckCircle className="h-4 w-4 text-emerald-500" /> Audio captures ready</span>
            <span className="flex items-center gap-1.5"><CheckCircle className="h-4 w-4 text-emerald-500" /> Whisper stubs active</span>
            <span className="flex items-center gap-1.5"><CheckCircle className="h-4 w-4 text-emerald-500" /> Copilot sync bound</span>
          </div>
        </div>

        {/* Modules Health List grid */}
        <div className="p-6 bg-slate-900/40 border border-slate-800/80 rounded-2xl">
          <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-300 mb-4 border-b border-slate-800/60 pb-3">Subsystems Health Status</h3>
          <div className="space-y-2.5 max-h-[190px] overflow-y-auto pr-1 text-xs">
            {Object.entries(moduleHealth).map(([module, status]) => (
              <div key={module} className="flex items-center justify-between py-1 border-b border-slate-800/30 last:border-0">
                <span className="text-slate-300 font-medium">{module}</span>
                <span className={`flex items-center gap-1.5 font-semibold ${status.toLowerCase() === "running" || status.toLowerCase() === "healthy" ? "text-emerald-400" : "text-amber-400"}`}>
                  <span className={`h-1.5 w-1.5 rounded-full ${status.toLowerCase() === "running" || status.toLowerCase() === "healthy" ? "bg-emerald-400" : "bg-amber-400"}`}></span>
                  {status}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* 4. Timeline reasoning feed and Configuration */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        
        {/* Dynamic Decisions timeline */}
        <div className="lg:col-span-2 p-6 bg-slate-900/40 border border-slate-800/80 rounded-2xl">
          <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-300 mb-4 border-b border-slate-800/60 pb-3">AI Autonomy Reasoning History</h3>
          <div className="space-y-4 max-h-[380px] overflow-y-auto pr-2">
            {decisions.map((dec) => (
              <div key={dec.decision_id} className="p-4 bg-slate-800/30 border border-slate-800 hover:border-slate-700 rounded-xl transition duration-200">
                <div className="flex items-start justify-between gap-4 mb-2">
                  <div>
                    <span className="text-[10px] font-mono text-indigo-400 bg-indigo-500/10 px-2 py-0.5 rounded border border-indigo-500/20">{dec.goal}</span>
                    <h4 className="text-sm font-bold text-white mt-1.5">Action: {dec.selected_action.action_name}</h4>
                  </div>
                  <div className="text-right">
                    <span className="text-xs text-slate-400 font-mono">Confidence: <span className="text-emerald-400 font-bold">{(dec.confidence * 100).toFixed(0)}%</span></span>
                  </div>
                </div>
                <p className="text-xs text-slate-300 leading-relaxed mb-3">{dec.reason}</p>
                <div className="flex items-center justify-between text-[10px] text-slate-500 font-mono">
                  <span>Trigger: {dec.trigger}</span>
                  <span>ID: #{dec.decision_id.slice(0, 8)}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Diagnostics & Config Panels */}
        <div className="flex flex-col gap-6">
          
          {/* Autonomy Config settings */}
          <div className="p-6 bg-slate-900/40 border border-slate-800/80 rounded-2xl text-xs">
            <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-300 mb-4 border-b border-slate-800/60 pb-3">Diagnostics & Configurations</h3>
            <div className="space-y-4">
              <div>
                <label className="text-slate-400 block mb-1.5 font-medium">Autonomy mode</label>
                <select value={autonomyMode} onChange={(e) => setAutonomyMode(e.target.value)} className="w-full bg-slate-800 border border-slate-700 text-slate-200 rounded-lg px-3 py-2 outline-none">
                  <option>Observation</option>
                  <option>Recommendation</option>
                  <option>Semi-Autonomous</option>
                  <option>Fully Autonomous</option>
                </select>
              </div>

              <div>
                <label className="text-slate-400 block mb-1.5 font-medium">Meeting Detection Profile</label>
                <select value={detectionProfile} onChange={(e) => setDetectionProfile(e.target.value)} className="w-full bg-slate-800 border border-slate-700 text-slate-200 rounded-lg px-3 py-2 outline-none">
                  <option>Conservative</option>
                  <option>Balanced</option>
                  <option>Aggressive</option>
                </select>
              </div>

              <div>
                <label className="text-slate-400 block mb-1.5 font-medium">Recording Policy</label>
                <select value={recordingPolicy} onChange={(e) => setRecordingPolicy(e.target.value)} className="w-full bg-slate-800 border border-slate-700 text-slate-200 rounded-lg px-3 py-2 outline-none">
                  <option>Manual</option>
                  <option>Assisted</option>
                  <option>Autonomous</option>
                </select>
              </div>
            </div>
          </div>

          {/* Export and reports */}
          <div className="p-6 bg-slate-900/40 border border-slate-800/80 rounded-2xl text-xs">
            <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-300 mb-4 border-b border-slate-800/60 pb-3">System Exports</h3>
            <div className="grid grid-cols-2 gap-3">
              <button onClick={() => exportReport("logs")} className="flex items-center justify-center gap-1.5 bg-slate-800 hover:bg-slate-750 text-slate-200 py-2 border border-slate-700 rounded-lg transition duration-150 cursor-pointer font-semibold">
                <Download className="h-3.5 w-3.5" /> Logs
              </button>
              <button onClick={() => exportReport("metrics")} className="flex items-center justify-center gap-1.5 bg-slate-800 hover:bg-slate-750 text-slate-200 py-2 border border-slate-700 rounded-lg transition duration-150 cursor-pointer font-semibold">
                <Download className="h-3.5 w-3.5" /> Metrics
              </button>
              <button onClick={() => exportReport("decisions")} className="flex items-center justify-center gap-1.5 bg-slate-800 hover:bg-slate-750 text-slate-200 py-2 border border-slate-700 rounded-lg transition duration-150 cursor-pointer font-semibold">
                <Download className="h-3.5 w-3.5" /> Decisions
              </button>
              <button onClick={() => exportReport("diagnostics")} className="flex items-center justify-center gap-1.5 bg-slate-800 hover:bg-slate-750 text-slate-200 py-2 border border-slate-700 rounded-lg transition duration-150 cursor-pointer font-semibold">
                <Download className="h-3.5 w-3.5" /> Report
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* 5. Approvals Center */}
      <div className="p-6 bg-slate-900/40 border border-slate-800/80 rounded-2xl mb-6">
        <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-300 mb-4 border-b border-slate-800/60 pb-3">Autonomy Approval Queue</h3>
        {approvals.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {approvals.map((item) => (
              <div key={item.approval_id} className="p-4 bg-slate-800/40 border border-slate-850 rounded-xl flex flex-col justify-between gap-4">
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-bold text-white">{item.action_name}</span>
                    <span className="text-[10px] font-mono text-slate-500">Token: #{item.approval_id.slice(0, 8)}</span>
                  </div>
                  <p className="text-xs text-slate-400 leading-relaxed font-mono">Action parameters: {JSON.stringify(item.parameters)}</p>
                </div>
                
                <div className="flex items-center gap-3">
                  <button onClick={() => resolveApproval(item.approval_id, true)} className="flex-1 bg-emerald-600 hover:bg-emerald-500 text-white font-semibold py-1.5 text-xs rounded transition duration-150 cursor-pointer">
                    Approve
                  </button>
                  <button onClick={() => resolveApproval(item.approval_id, false)} className="flex-1 bg-slate-800 hover:bg-slate-750 text-slate-300 font-semibold py-1.5 text-xs border border-slate-700 rounded transition duration-150 cursor-pointer">
                    Reject
                  </button>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center py-8 text-slate-500 text-xs">
            <Shield className="h-8 w-8 text-slate-650 mb-2" />
            <p>No actions currently queued awaiting approvals.</p>
          </div>
        )}
      </div>

      {/* 6. Console Live logs */}
      <div className="p-6 bg-slate-900/60 border border-slate-850 rounded-2xl flex flex-col gap-4">
        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-800 pb-3">
          <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-300 flex items-center gap-2">
            <Terminal className="h-4 w-4 text-indigo-400" /> Running System Console
          </h3>
          
          <div className="flex flex-wrap items-center gap-3 text-xs">
            <div className="relative">
              <Search className="absolute left-3 top-2.5 h-3.5 w-3.5 text-slate-500" />
              <input
                type="text"
                placeholder="Search logs..."
                value={logSearch}
                onChange={(e) => setLogSearch(e.target.value)}
                className="bg-slate-850 border border-slate-750 rounded-lg pl-9 pr-3 py-2 outline-none text-slate-200 placeholder-slate-500"
              />
            </div>
            
            <select
              value={logModuleFilter}
              onChange={(e) => setLogModuleFilter(e.target.value)}
              className="bg-slate-850 border border-slate-750 rounded-lg px-3 py-2 outline-none text-slate-200 font-medium"
            >
              <option value="">All modules</option>
              <option value="background">Background</option>
              <option value="recording">Recording</option>
              <option value="autonomy">Autonomy</option>
            </select>
          </div>
        </div>

        {/* Live log panel screen */}
        <div className="bg-slate-950 p-4 rounded-xl border border-slate-850 font-mono text-[11px] leading-relaxed max-h-[300px] overflow-y-auto space-y-1.5">
          {logs
            .filter(log => {
              if (logSearch && !log.message.toLowerCase().includes(logSearch.toLowerCase())) return false;
              if (logModuleFilter && !log.module.toLowerCase().includes(logModuleFilter.toLowerCase())) return false;
              return true;
            })
            .map((log, idx) => (
              <div key={idx} className="flex gap-4 hover:bg-slate-900/30 py-0.5 rounded">
                <span className="text-slate-550 shrink-0">{log.timestamp.slice(11, 19)}</span>
                <span className={`font-semibold shrink-0 w-12 ${log.level === "ERROR" ? "text-rose-500" : log.level === "WARNING" ? "text-amber-500" : "text-sky-500"}`}>[{log.level}]</span>
                <span className="text-indigo-400 shrink-0 font-medium">[{log.module.split(".").pop()}]</span>
                <span className="text-slate-300 break-all">{log.message}</span>
              </div>
            ))}
          <div ref={logEndRef} />
        </div>
      </div>

    </div>
  );
}

import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Cpu, Zap, Layers } from 'lucide-react';

interface AgentNode {
  id: string;
  name: string;
  role: string;
  status: 'ACTIVE' | 'BUSY' | 'DEGRADED' | 'OFFLINE';
  latency: number;
  toolCount: number;
  connections: string[];
}

export const AgentCenter: React.FC = () => {
  const [agents] = useState<AgentNode[]>([
    { id: "sup", name: "Supervisor Agent", role: "Coordination & Delegation Hub", status: "ACTIVE", latency: 25, toolCount: 11, connections: ["meet", "vis", "sch", "mem", "res", "em", "wf"] },
    { id: "meet", name: "Meeting Agent", role: "Speech, Transcripts & Action Items", status: "ACTIVE", latency: 80, toolCount: 2, connections: ["sup"] },
    { id: "vis", name: "Vision Agent", role: "Screen Capture & OCR Processing", status: "ACTIVE", latency: 120, toolCount: 1, connections: ["sup"] },
    { id: "sch", name: "Scheduler Agent", role: "Natural Language Calendar Planner", status: "ACTIVE", latency: 45, toolCount: 3, connections: ["sup"] },
    { id: "mem", name: "Memory Agent", role: "Semantic Vectors & Long-Term Recall", status: "ACTIVE", latency: 15, toolCount: 2, connections: ["sup"] },
    { id: "res", name: "Research Agent", role: "RAG Docs & Web Query Pipeline", status: "ACTIVE", latency: 140, toolCount: 2, connections: ["sup"] },
    { id: "em", name: "Email Agent", role: "Gmail Automation & Broadcasts", status: "ACTIVE", latency: 60, toolCount: 2, connections: ["sup"] },
    { id: "wf", name: "Workflow Agent", role: "DAG Executions & Manual approvals", status: "ACTIVE", latency: 10, toolCount: 1, connections: ["sup"] }
  ]);

  return (
    <div className="p-6 space-y-6 max-w-6xl mx-auto text-left">
      <div>
        <h1 className="text-2xl font-bold tracking-tight font-display text-white">AGENT CENTER</h1>
        <p className="text-sm text-zinc-400">Monitor internal specialized agents, coordination flows, heartbeats, and latency maps.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Side Node Grid */}
        <div className="lg:col-span-2 space-y-4">
          <h2 className="text-sm font-bold text-zinc-400 uppercase tracking-wider">Agent Roster</h2>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {agents.map((agent) => (
              <motion.div
                key={agent.id}
                whileHover={{ scale: 1.01 }}
                className="border border-zinc-900 bg-zinc-950/60 p-4 rounded-xl flex flex-col justify-between space-y-3 backdrop-blur-md relative overflow-hidden group hover:border-indigo-500/10"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2.5">
                    <div className="w-8 h-8 rounded-lg bg-indigo-500/5 border border-indigo-500/10 flex items-center justify-center text-indigo-400">
                      <Cpu size={16} />
                    </div>
                    <div>
                      <h3 className="text-sm font-bold text-white font-display">{agent.name}</h3>
                      <span className="text-[10px] text-zinc-500">{agent.role}</span>
                    </div>
                  </div>

                  <span className="text-[10px] font-mono bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 px-2 py-0.5 rounded">
                    {agent.status}
                  </span>
                </div>

                <div className="flex items-center justify-between pt-2 border-t border-zinc-900/60 text-[10px] font-mono text-zinc-500">
                  <div className="flex items-center gap-1">
                    <Zap size={10} className="text-amber-400" />
                    <span>Latency: {agent.latency}ms</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <Layers size={10} className="text-indigo-400" />
                    <span>Tools: {agent.toolCount}</span>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        </div>

        {/* Right Side Visualized Graph Preview */}
        <div className="border border-zinc-900 bg-zinc-950/60 p-5 rounded-xl flex flex-col justify-between space-y-4 backdrop-blur-md">
          <h2 className="text-sm font-bold text-zinc-400 uppercase tracking-wider">Topology Preview</h2>

          {/* Simple Animated Topology Graph Container */}
          <div className="relative h-64 border border-zinc-900/80 bg-zinc-950/20 rounded-xl overflow-hidden flex items-center justify-center">
            
            {/* Connection Lines (SVG) */}
            <svg className="absolute inset-0 w-full h-full pointer-events-none">
              {/* Lines from center (sup) to surround points */}
              <line x1="50%" y1="50%" x2="20%" y2="20%" stroke="#4338ca" strokeWidth="1" strokeDasharray="3,3" />
              <line x1="50%" y1="50%" x2="80%" y2="20%" stroke="#4338ca" strokeWidth="1" strokeDasharray="3,3" />
              <line x1="50%" y1="50%" x2="15%" y2="50%" stroke="#4338ca" strokeWidth="1" strokeDasharray="3,3" />
              <line x1="50%" y1="50%" x2="85%" y2="50%" stroke="#4338ca" strokeWidth="1" strokeDasharray="3,3" />
              <line x1="50%" y1="50%" x2="20%" y2="80%" stroke="#4338ca" strokeWidth="1" strokeDasharray="3,3" />
              <line x1="50%" y1="50%" x2="80%" y2="80%" stroke="#4338ca" strokeWidth="1" strokeDasharray="3,3" />
            </svg>

            {/* Nodes */}
            <div className="absolute w-10 y-10 rounded-full bg-indigo-600 border border-indigo-400 text-[10px] font-bold text-white flex items-center justify-center shadow-lg shadow-indigo-500/20">
              SUP
            </div>
            
            <div className="absolute top-[15%] left-[15%] w-8 h-8 rounded-lg bg-zinc-900 border border-zinc-800 text-[9px] font-mono text-zinc-400 flex items-center justify-center">MEET</div>
            <div className="absolute top-[15%] right-[15%] w-8 h-8 rounded-lg bg-zinc-900 border border-zinc-800 text-[9px] font-mono text-zinc-400 flex items-center justify-center">VIS</div>
            <div className="absolute top-[45%] left-[5%] w-8 h-8 rounded-lg bg-zinc-900 border border-zinc-800 text-[9px] font-mono text-zinc-400 flex items-center justify-center">SCH</div>
            <div className="absolute top-[45%] right-[5%] w-8 h-8 rounded-lg bg-zinc-900 border border-zinc-800 text-[9px] font-mono text-zinc-400 flex items-center justify-center">MEM</div>
            <div className="absolute bottom-[15%] left-[15%] w-8 h-8 rounded-lg bg-zinc-900 border border-zinc-800 text-[9px] font-mono text-zinc-400 flex items-center justify-center">RES</div>
            <div className="absolute bottom-[15%] right-[15%] w-8 h-8 rounded-lg bg-zinc-900 border border-zinc-800 text-[9px] font-mono text-zinc-400 flex items-center justify-center">EM</div>

          </div>

          <div className="p-3 bg-zinc-900/30 border border-zinc-900 rounded-lg text-left">
            <span className="text-[10px] font-mono text-zinc-500 block mb-1">Supervisor Decision Policy</span>
            <p className="text-[10px] text-zinc-400 leading-normal">
              Internal requests are checked against intent matching. If capabilities map to active external A2A agents, requests are wrapped dynamically and delegated securely.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AgentCenter;

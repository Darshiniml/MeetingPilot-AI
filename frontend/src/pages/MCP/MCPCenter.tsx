import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Database, RefreshCw } from 'lucide-react';

interface MCPProvider {
  name: string;
  toolsCount: number;
  latencyMs: number;
  status: 'healthy' | 'degraded' | 'offline';
  capabilities: string[];
}

export const MCPCenter: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [providers] = useState<MCPProvider[]>([
    { name: "github", toolsCount: 3, latencyMs: 140, status: 'healthy', capabilities: ["search_issues", "create_issue", "list_prs"] },
    { name: "slack", toolsCount: 2, latencyMs: 65, status: 'healthy', capabilities: ["send_message", "list_channels"] },
    { name: "notion", toolsCount: 2, latencyMs: 190, status: 'healthy', capabilities: ["create_page", "search_notes"] },
    { name: "google_drive", toolsCount: 1, latencyMs: 95, status: 'healthy', capabilities: ["search_files"] },
    { name: "jira", toolsCount: 1, latencyMs: 120, status: 'healthy', capabilities: ["search_issues"] },
    { name: "salesforce", toolsCount: 1, latencyMs: 170, status: 'healthy', capabilities: ["create_lead"] },
    { name: "teams", toolsCount: 1, latencyMs: 80, status: 'healthy', capabilities: ["send_chat"] },
    { name: "servicenow", toolsCount: 1, latencyMs: 210, status: 'healthy', capabilities: ["create_incident"] }
  ]);

  const refreshData = () => {
    setLoading(true);
    setTimeout(() => {
      setLoading(false);
    }, 800);
  };

  return (
    <div className="p-6 space-y-6 max-w-6xl mx-auto text-left">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight font-display text-white">MODEL CONTEXT PROTOCOL (MCP) CENTER</h1>
          <p className="text-sm text-zinc-400">Manage external tool contexts, capabilities, and schemas loaded into the agent core.</p>
        </div>
        <button
          onClick={refreshData}
          className="p-2 rounded-lg bg-zinc-900 border border-zinc-800 text-zinc-400 hover:text-white transition-colors cursor-pointer"
        >
          <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {providers.map((prov, index) => (
          <motion.div
            key={prov.name}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.04 }}
            className="border border-zinc-900 bg-zinc-950/60 p-5 rounded-xl flex flex-col justify-between space-y-4 backdrop-blur-md relative overflow-hidden group hover:border-indigo-500/10"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-lg bg-indigo-500/5 border border-indigo-500/10 flex items-center justify-center text-indigo-400">
                  <Database size={16} />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-white font-display uppercase">{prov.name}</h3>
                  <span className="text-[10px] text-zinc-500 font-mono">{prov.toolsCount} Tools Active</span>
                </div>
              </div>

              <div className="flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                <span className="text-[10px] font-mono text-zinc-400 uppercase">{prov.status}</span>
              </div>
            </div>

            <div className="space-y-1.5">
              <span className="text-[10px] font-mono text-zinc-500 block">Exposed Context Actions</span>
              <div className="flex flex-wrap gap-1.5">
                {prov.capabilities.map(cap => (
                  <div key={cap} className="px-2 py-0.5 rounded bg-zinc-900 border border-zinc-800/80 text-[10px] text-zinc-400 font-mono">
                    {cap}
                  </div>
                ))}
              </div>
            </div>

            <div className="flex items-center justify-between pt-2 border-t border-zinc-900 text-[10px] font-mono text-zinc-500">
              <span>Avg Latency</span>
              <span className="text-zinc-300">{prov.latencyMs}ms</span>
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  );
};

export default MCPCenter;

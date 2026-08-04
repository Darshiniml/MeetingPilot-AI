import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import api from '../../services/api';
import { Network, Activity, ShieldCheck, RefreshCw, Zap, ServerCrash } from 'lucide-react';

interface AgentMetrics {
  a2a_requests: number;
  fallback_count: number;
  success_count: number;
  success_rate: number;
  average_latency_ms: number;
  timeout_count: number;
}

interface Capability {
  capability_id: string;
  name: string;
  version: string;
  provider: string;
  required_permissions: string[];
  input_schema: Record<string, any>;
  output_schema: Record<string, any>;
  health: string;
}

interface ExternalAgent {
  agent_name: string;
  version: string;
  health_status: string;
  circuit_state: string;
  capabilities: Capability[];
}

export const A2ACenter: React.FC = () => {
  const [metrics, setMetrics] = useState<AgentMetrics>({
    a2a_requests: 0,
    fallback_count: 0,
    success_count: 0,
    success_rate: 1.0,
    average_latency_ms: 0.0,
    timeout_count: 0
  });

  const [agents, setAgents] = useState<ExternalAgent[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchA2AData = async () => {
    try {
      setLoading(true);
      const [mRes, dRes] = await Promise.all([
        api.get('/api/a2a/metrics'),
        api.get('/api/a2a/discovery')
      ]);
      setMetrics(mRes.data);
      setAgents(dRes.data);
    } catch (err) {
      console.error("Failed to load A2A registry details:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchA2AData();
    const interval = setInterval(fetchA2AData, 20000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="p-6 space-y-6 max-w-6xl mx-auto text-left">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight font-display text-white">AGENT-TO-AGENT (A2A) ROUTER</h1>
          <p className="text-sm text-zinc-400">Secure routing, capability negotiation, and load balancing for external federated agents.</p>
        </div>
        <button
          onClick={fetchA2AData}
          className="p-2 rounded-lg bg-zinc-900 border border-zinc-800 text-zinc-400 hover:text-white transition-colors cursor-pointer"
        >
          <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
        </button>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: "A2A Requests", val: metrics.a2a_requests, icon: <Network size={16} className="text-indigo-400" /> },
          { label: "Avg Latency", val: `${metrics.average_latency_ms.toFixed(1)}ms`, icon: <Zap size={16} className="text-amber-400" /> },
          { label: "Success Rate", val: `${(metrics.success_rate * 100).toFixed(0)}%`, icon: <ShieldCheck size={16} className="text-emerald-400" /> },
          { label: "Circuit Fallbacks", val: metrics.fallback_count, icon: <ServerCrash size={16} className="text-red-400" /> }
        ].map((item, idx) => (
          <div key={idx} className="border border-zinc-900 bg-zinc-950/60 p-4 rounded-xl space-y-1 backdrop-blur-md">
            <div className="flex items-center justify-between text-zinc-500 text-xs">
              <span>{item.label}</span>
              {item.icon}
            </div>
            <div className="text-lg font-bold text-white font-mono">{item.val}</div>
          </div>
        ))}
      </div>

      {/* Registered Agents Grid */}
      <div className="space-y-4">
        <h2 className="text-base font-bold text-zinc-300 font-display flex items-center gap-2">
          <Activity size={18} className="text-indigo-400" />
          <span>Active Federated Roster</span>
        </h2>

        {loading && agents.length === 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {[1, 2].map(n => (
              <div key={n} className="h-44 border border-zinc-900 bg-zinc-950/20 rounded-xl shimmer" />
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {agents.map((agent, index) => {
              const isActive = agent.health_status === "ACTIVE";
              const isDegraded = agent.health_status === "DEGRADED" || agent.circuit_state === "OPEN";
              return (
                <motion.div
                  key={agent.agent_name}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.05 }}
                  className="border border-zinc-900/80 bg-zinc-950/60 p-5 rounded-xl flex flex-col justify-between space-y-4 backdrop-blur-md relative overflow-hidden group hover:border-indigo-500/20"
                >
                  {/* Status Indicator */}
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <div className="w-8 h-8 rounded-lg bg-zinc-900 border border-zinc-800 flex items-center justify-center font-bold text-white uppercase text-xs">
                        {agent.agent_name.slice(0, 2)}
                      </div>
                      <div>
                        <h3 className="text-sm font-bold text-white font-display uppercase">{agent.agent_name} Agent</h3>
                        <span className="text-[10px] text-zinc-500 font-mono">v{agent.version}</span>
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      {/* Health state */}
                      <span className={`text-[10px] font-mono px-2 py-0.5 rounded border ${
                        isActive
                          ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-400"
                          : isDegraded
                          ? "bg-red-500/10 border-red-500/20 text-red-400"
                          : "bg-zinc-800 border-zinc-700 text-zinc-400"
                      }`}>
                        {agent.health_status}
                      </span>
                      
                      {/* Circuit state */}
                      <span className={`text-[10px] font-mono px-2 py-0.5 rounded border ${
                        agent.circuit_state === "CLOSED"
                          ? "bg-zinc-900 border-zinc-800 text-zinc-500"
                          : "bg-amber-500/10 border-amber-500/20 text-amber-400"
                      }`}>
                        CB: {agent.circuit_state}
                      </span>
                    </div>
                  </div>

                  {/* Capabilities List */}
                  <div className="space-y-2">
                    <span className="text-[10px] font-mono text-zinc-500 block">Exposed Capabilities ({agent.capabilities.length})</span>
                    <div className="flex flex-wrap gap-2">
                      {agent.capabilities.map((cap) => (
                        <div
                          key={cap.capability_id}
                          className="px-2 py-1 rounded bg-zinc-900/60 border border-zinc-800/80 text-[10px] text-zinc-400 hover:text-white cursor-pointer font-mono"
                          title={`ID: ${cap.capability_id}\nRequired permissions: ${cap.required_permissions.join(", ") || "None"}`}
                        >
                          {cap.name}
                        </div>
                      ))}
                    </div>
                  </div>
                </motion.div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};

export default A2ACenter;

import React, { useState } from 'react';
import { Layers } from 'lucide-react';

interface Step {
  name: string;
  tool: string;
  status: 'COMPLETED' | 'FAILED' | 'RUNNING' | 'QUEUED' | 'WAITING_APPROVAL';
  durationMs: number;
}

interface WorkflowRun {
  id: string;
  name: string;
  status: 'COMPLETED' | 'FAILED' | 'RUNNING' | 'WAITING_APPROVAL';
  durationMs: number;
  steps: Step[];
  timestamp: string;
}

export const WorkflowCenter: React.FC = () => {
  const [runs] = useState<WorkflowRun[]>([
    {
      id: "wf-run-1",
      name: "Meeting Finished Pipeline",
      status: "COMPLETED",
      durationMs: 450,
      timestamp: "Today, 10:24 AM",
      steps: [
        { name: "Generate Summary", tool: "summary", status: "COMPLETED", durationMs: 120 },
        { name: "Extract Action Items", tool: "action_items", status: "COMPLETED", durationMs: 100 },
        { name: "Refresh Memory Store", tool: "memory", status: "COMPLETED", durationMs: 80 },
        { name: "Refresh Semantic Embeddings", tool: "memory", status: "COMPLETED", durationMs: 150 }
      ]
    },
    {
      id: "wf-run-2",
      name: "Customer Escalation Workflow",
      status: "WAITING_APPROVAL",
      durationMs: 220,
      timestamp: "Today, 11:05 AM",
      steps: [
        { name: "Risk Detection Trigger", tool: "copilot", status: "COMPLETED", durationMs: 40 },
        { name: "Generate Executive Summary", tool: "summary", status: "COMPLETED", durationMs: 180 },
        { name: "Send Alert Broadcast", tool: "slack", status: "WAITING_APPROVAL", durationMs: 0 },
        { name: "Send Executive Email", tool: "gmail", status: "QUEUED", durationMs: 0 }
      ]
    }
  ]);

  const [selectedRun, setSelectedRun] = useState<WorkflowRun | null>(runs[0]);

  return (
    <div className="p-6 space-y-6 max-w-6xl mx-auto text-left">
      <div>
        <h1 className="text-2xl font-bold tracking-tight font-display text-white">WORKFLOW CENTER</h1>
        <p className="text-sm text-zinc-400">Track DAG executions, validation stats, step runs, and compensation rollback audit logs.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Run list (Left) */}
        <div className="md:col-span-1 space-y-3">
          <span className="text-[10px] font-mono text-zinc-500 uppercase tracking-wider block">Execution Queue</span>
          
          <div className="space-y-2">
            {runs.map((run) => {
              const isSelected = selectedRun?.id === run.id;
              return (
                <button
                  key={run.id}
                  onClick={() => setSelectedRun(run)}
                  className={`w-full text-left p-3.5 rounded-xl border transition-all cursor-pointer block ${
                    isSelected
                      ? "border-indigo-500/25 bg-indigo-500/5"
                      : "border-zinc-900 bg-zinc-950/60 hover:bg-zinc-900/60"
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-[10px] text-zinc-500 font-mono">{run.timestamp}</span>
                    <span className={`text-[9px] font-mono px-1.5 py-0.5 rounded ${
                      run.status === "COMPLETED"
                        ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                        : run.status === "WAITING_APPROVAL"
                        ? "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                        : "bg-zinc-900 text-zinc-400"
                    }`}>
                      {run.status}
                    </span>
                  </div>

                  <h4 className="text-xs font-bold text-white font-display mb-1">{run.name}</h4>
                  
                  <div className="flex items-center justify-between text-[10px] font-mono text-zinc-500">
                    <span>Steps: {run.steps.length}</span>
                    <span>{run.durationMs}ms</span>
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Selected execution graph / stats (Right) */}
        <div className="md:col-span-2 border border-zinc-900 bg-zinc-950/60 p-5 rounded-xl backdrop-blur-md text-left flex flex-col justify-between">
          {selectedRun ? (
            <div className="space-y-6">
              <div className="flex items-center justify-between border-b border-zinc-900 pb-3">
                <div>
                  <h3 className="text-sm font-bold text-white font-display uppercase">{selectedRun.name}</h3>
                  <span className="text-[10px] text-zinc-500 font-mono">Run ID: {selectedRun.id}</span>
                </div>

                <div className="text-right">
                  <span className="text-[10px] font-mono text-zinc-500 block">Total Duration</span>
                  <span className="text-sm font-bold text-indigo-400 font-mono">{selectedRun.durationMs}ms</span>
                </div>
              </div>

              {/* Execution steps sequence */}
              <div className="space-y-3.5 relative pl-4 border-l border-zinc-900">
                {selectedRun.steps.map((step, idx) => {
                  const isDone = step.status === "COMPLETED";
                  const isWaiting = step.status === "WAITING_APPROVAL";
                  
                  return (
                    <div key={idx} className="relative flex items-center justify-between">
                      {/* Left Dot */}
                      <span className={`absolute -left-[20.5px] w-2.5 h-2.5 rounded-full border ${
                        isDone
                          ? "bg-emerald-400 border-emerald-500 shadow-sm shadow-emerald-500/20"
                          : isWaiting
                          ? "bg-amber-400 border-amber-500 animate-pulse"
                          : "bg-zinc-800 border-zinc-700"
                      }`} />

                      <div>
                        <h4 className="text-xs font-bold text-slate-200">{step.name}</h4>
                        <span className="text-[10px] text-zinc-500 font-mono">Tool: {step.tool}</span>
                      </div>

                      <div className="text-right">
                        <span className={`text-[9px] font-mono px-2 py-0.5 rounded ${
                          isDone
                            ? "bg-emerald-500/5 text-emerald-500"
                            : isWaiting
                            ? "bg-amber-500/5 text-amber-500"
                            : "bg-zinc-900 text-zinc-600"
                        }`}>
                          {step.status}
                        </span>
                        {isDone && <span className="text-[9px] text-zinc-500 font-mono block mt-0.5">{step.durationMs}ms</span>}
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Audit trail */}
              <div className="p-3 bg-zinc-900/40 border border-zinc-800/80 rounded-lg text-[10px] leading-relaxed text-zinc-400">
                <span className="font-bold text-zinc-300 block mb-1">State Log Summary</span>
                {selectedRun.status === "WAITING_APPROVAL" ? (
                  <span>Workflow paused at step <b>'Send Alert Broadcast'</b>. Awaiting manual parameter validation or approval. Check the Approvals Center to proceed.</span>
                ) : (
                  <span>Workflow runs completed successfully. Indexing results into long-term semantic memory blocks. No rollbacks or compensations triggered.</span>
                )}
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center py-20 text-zinc-500 space-y-2">
              <Layers className="w-10 h-10 text-zinc-700" />
              <span>Select an execution run to view step details</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default WorkflowCenter;

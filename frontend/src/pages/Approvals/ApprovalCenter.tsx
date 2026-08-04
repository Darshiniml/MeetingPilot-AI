import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Check, X, Edit3, UserPlus, Clock, CheckCircle } from 'lucide-react';

interface ApprovalTask {
  id: string;
  workflowName: string;
  stepName: string;
  triggeredBy: string;
  timestamp: string;
  parameters: Record<string, any>;
  description: string;
}

export const ApprovalCenter: React.FC = () => {
  const [tasks, setTasks] = useState<ApprovalTask[]>([
    {
      id: "app-1",
      workflowName: "Meeting Scheduled Pipeline",
      stepName: "Send Gmail Invitation",
      triggeredBy: "Scheduler Agent",
      timestamp: "Today, 10:24 AM",
      description: "Approve draft email invitations to stakeholders for the board review.",
      parameters: {
        to: "investors@group.com, board@company.com",
        subject: "Q3 Board Review & Planning",
        template: "standard_invitation"
      }
    },
    {
      id: "app-2",
      workflowName: "Customer Escalation Workflow",
      stepName: "Send Alert Broadcast",
      triggeredBy: "Risk Detector",
      timestamp: "Today, 11:05 AM",
      description: "Send escalations to Slack channel #executive-alerts regarding high-priority SLA risk.",
      parameters: {
        channel: "#executive-alerts",
        priority: "CRITICAL",
        summary: "SLA escalation warning triggered during customer sync."
      }
    }
  ]);

  const [activeTask, setActiveTask] = useState<ApprovalTask | null>(null);
  const [modalType, setModalType] = useState<'modify' | 'delegate' | 'postpone' | null>(null);
  const [modifiedParams, setModifiedParams] = useState<string>("");
  const [delegateEmail, setDelegateEmail] = useState<string>("");
  const [postponeTime, setPostponeTime] = useState<string>("1 hour");

  const handleAction = (id: string, action: string, feedbackMsg: string) => {
    setTasks(tasks.filter(t => t.id !== id));
    setActiveTask(null);
    setModalType(null);
    // Trigger window event to show toast
    const event = new CustomEvent('show-toast', {
      detail: { type: 'success', title: `Task ${action}`, message: feedbackMsg }
    });
    window.dispatchEvent(event);
  };

  return (
    <div className="p-6 space-y-6 max-w-6xl mx-auto text-left">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight font-display text-white">APPROVAL CENTER</h1>
          <p className="text-sm text-zinc-400">Review, modify, delegate, or approve tasks paused at manual gate steps.</p>
        </div>
        <div className="px-3 py-1 rounded-full bg-zinc-900 border border-zinc-800 text-xs font-mono text-zinc-400">
          Pending Gates: {tasks.length}
        </div>
      </div>

      <AnimatePresence mode="popLayout">
        {tasks.length === 0 ? (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="p-12 text-center border border-dashed border-zinc-800 rounded-2xl bg-zinc-900/10 backdrop-blur-sm flex flex-col items-center justify-center space-y-3"
          >
            <CheckCircle className="w-12 h-12 text-emerald-500/20" />
            <h3 className="text-lg font-bold text-zinc-300">All Clear</h3>
            <p className="text-sm text-zinc-500 max-w-md">No workflows are currently waiting at manual approval gates. Your automated pipelines are running smoothly.</p>
          </motion.div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {tasks.map((task) => (
              <motion.div
                key={task.id}
                layout
                initial={{ opacity: 0, scale: 0.98 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.98 }}
                whileHover={{ y: -4 }}
                transition={{ duration: 0.2 }}
                className="border border-zinc-800/80 hover:border-indigo-500/30 bg-zinc-950/60 rounded-xl p-5 shadow-xl flex flex-col justify-between space-y-4 backdrop-blur-md relative overflow-hidden group"
              >
                <div className="absolute top-0 right-0 w-24 h-24 bg-indigo-500/5 rounded-full blur-2xl group-hover:bg-indigo-500/10 transition-all duration-300" />
                
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-mono text-indigo-400 bg-indigo-500/5 px-2 py-0.5 rounded border border-indigo-500/10">
                      {task.workflowName}
                    </span>
                    <span className="text-[10px] text-zinc-500">{task.timestamp}</span>
                  </div>
                  
                  <h3 className="text-base font-bold text-white font-display flex items-center gap-1.5">
                    {task.stepName}
                  </h3>
                  
                  <p className="text-xs text-zinc-400 leading-relaxed">
                    {task.description}
                  </p>

                  <div className="p-3 bg-zinc-900/40 border border-zinc-800/50 rounded-lg text-left">
                    <span className="text-[10px] font-mono text-zinc-500 block mb-1">Parameters</span>
                    <pre className="text-[10px] font-mono text-zinc-300 overflow-x-auto">
                      {JSON.stringify(task.parameters, null, 2)}
                    </pre>
                  </div>
                </div>

                {/* Primary Action Buttons */}
                <div className="flex flex-wrap gap-2 pt-2 border-t border-zinc-900">
                  <button
                    onClick={() => handleAction(task.id, 'Approved', 'Workflow step resumed successfully.')}
                    className="flex-1 min-w-[80px] py-2 px-3 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs flex items-center justify-center gap-1 transition-colors cursor-pointer"
                  >
                    <Check size={14} />
                    <span>Approve</span>
                  </button>
                  
                  <button
                    onClick={() => handleAction(task.id, 'Rejected', 'Workflow execution halted and rollbacks run.')}
                    className="flex-1 min-w-[80px] py-2 px-3 rounded-lg bg-zinc-900 border border-zinc-800 hover:bg-zinc-800 text-red-400 font-semibold text-xs flex items-center justify-center gap-1 transition-colors cursor-pointer"
                  >
                    <X size={14} />
                    <span>Reject</span>
                  </button>
                  
                  <button
                    onClick={() => {
                      setActiveTask(task);
                      setModifiedParams(JSON.stringify(task.parameters, null, 2));
                      setModalType('modify');
                    }}
                    className="p-2 rounded-lg bg-zinc-900 border border-zinc-800 text-zinc-400 hover:text-white transition-colors cursor-pointer"
                    title="Modify parameters"
                  >
                    <Edit3 size={14} />
                  </button>

                  <button
                    onClick={() => {
                      setActiveTask(task);
                      setModalType('delegate');
                    }}
                    className="p-2 rounded-lg bg-zinc-900 border border-zinc-800 text-zinc-400 hover:text-white transition-colors cursor-pointer"
                    title="Delegate review"
                  >
                    <UserPlus size={14} />
                  </button>

                  <button
                    onClick={() => {
                      setActiveTask(task);
                      setModalType('postpone');
                    }}
                    className="p-2 rounded-lg bg-zinc-900 border border-zinc-800 text-zinc-400 hover:text-white transition-colors cursor-pointer"
                    title="Postpone execution"
                  >
                    <Clock size={14} />
                  </button>
                </div>
              </motion.div>
            ))}
          </div>
        )}
      </AnimatePresence>

      {/* Action Modals */}
      {modalType && activeTask && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <motion.div
            initial={{ scale: 0.95, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            className="bg-zinc-950 border border-zinc-800 rounded-xl p-5 max-w-md w-full space-y-4 shadow-2xl"
          >
            <h3 className="text-base font-bold text-white font-display">
              {modalType === 'modify' && "Modify Parameters"}
              {modalType === 'delegate' && "Delegate Review Task"}
              {modalType === 'postpone' && "Postpone Step Execution"}
            </h3>

            {modalType === 'modify' && (
              <div className="space-y-2 text-left">
                <label className="text-[10px] font-mono text-zinc-500">Edit JSON Config</label>
                <textarea
                  value={modifiedParams}
                  onChange={(e) => setModifiedParams(e.target.value)}
                  rows={6}
                  className="w-full bg-zinc-900 border border-zinc-800 rounded-lg p-2.5 font-mono text-xs text-zinc-300 focus:outline-none focus:border-indigo-500"
                />
              </div>
            )}

            {modalType === 'delegate' && (
              <div className="space-y-2 text-left">
                <label className="text-[10px] font-mono text-zinc-500">Reassign Target Email</label>
                <input
                  type="email"
                  placeholder="manager@company.com"
                  value={delegateEmail}
                  onChange={(e) => setDelegateEmail(e.target.value)}
                  className="w-full bg-zinc-900 border border-zinc-800 rounded-lg p-2.5 text-xs text-zinc-300 focus:outline-none focus:border-indigo-500"
                />
              </div>
            )}

            {modalType === 'postpone' && (
              <div className="space-y-2 text-left">
                <label className="text-[10px] font-mono text-zinc-500">Select Postponement Duration</label>
                <select
                  value={postponeTime}
                  onChange={(e) => setPostponeTime(e.target.value)}
                  className="w-full bg-zinc-900 border border-zinc-800 rounded-lg p-2.5 text-xs text-zinc-300 focus:outline-none focus:border-indigo-500 cursor-pointer"
                >
                  <option value="30 mins">30 Minutes</option>
                  <option value="1 hour">1 Hour</option>
                  <option value="4 hours">4 Hours</option>
                  <option value="Tomorrow">1 Day (Tomorrow)</option>
                </select>
              </div>
            )}

            <div className="flex gap-2 justify-end">
              <button
                onClick={() => {
                  setModalType(null);
                  setActiveTask(null);
                }}
                className="px-3 py-1.5 rounded-lg border border-zinc-800 bg-zinc-900 hover:bg-zinc-800 text-zinc-400 hover:text-white text-xs font-semibold cursor-pointer"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  if (modalType === 'modify') {
                    try {
                      JSON.parse(modifiedParams);
                      handleAction(activeTask.id, 'Modified & Approved', 'Parameters updated and workflow resumed.');
                    } catch (e) {
                      alert("Invalid JSON format!");
                    }
                  } else if (modalType === 'delegate') {
                    if (!delegateEmail) return;
                    handleAction(activeTask.id, 'Delegated', `Review task delegated to ${delegateEmail}.`);
                  } else {
                    handleAction(activeTask.id, 'Postponed', `Step execution postponed by ${postponeTime}.`);
                  }
                }}
                className="px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold cursor-pointer"
              >
                Submit Action
              </button>
            </div>
          </motion.div>
        </div>
      )}
    </div>
  );
};

export default ApprovalCenter;

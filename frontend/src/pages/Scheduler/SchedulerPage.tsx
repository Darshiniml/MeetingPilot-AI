import React, { useState } from 'react';
import api from '../../services/api';
import { motion } from 'framer-motion';
import {
  CalendarDays,
  Sparkles,
  UserCheck,
  AlertTriangle,
  MailOpen,
  CalendarCheck,
  ExternalLink,
  Loader2
} from 'lucide-react';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { Badge } from '../../components/ui/Badge';
import { useToastStore } from '../../store/useToastStore';
import { LoadingSpinner } from '../../components/ui/LoadingSpinner';

interface AttendeeResolution {
  input_name: string;
  resolved_email: string | null;
  status: 'RESOLVED' | 'AMBIGUOUS' | 'NOT_FOUND';
  confidence_score: number;
  source: string;
  candidates: { name: string; email: string }[];
}

interface CalendarPreview {
  provider: string;
  available: boolean;
  conflicts: string[];
  suggestions: string[];
}

interface PlanResult {
  title: string;
  date: string;
  time: string;
  duration: string;
  timezone: string;
  attendees: string[];
  email_draft: string;
  calendar_preview: CalendarPreview;
  attendee_resolutions: AttendeeResolution[];
}

export const SchedulerPage: React.FC = () => {
  const [prompt, setPrompt] = useState('');
  const [loading, setLoading] = useState(false);
  const [scheduling, setScheduling] = useState(false);
  const [sendingInvites, setSendingInvites] = useState(false);
  
  const [plan, setPlan] = useState<PlanResult | null>(null);
  const [scheduledEvent, setScheduledEvent] = useState<{
    event_id: string;
    meet_link?: string;
    calendar_url?: string;
    meeting_id?: number;
  } | null>(null);

  const { addToast } = useToastStore();

  const suggestions = [
    "Schedule a Sync with Alice Vance about designs next Tuesday at 2 PM",
    "Meet with Bob Miller for 30 minutes tomorrow at 10 AM",
    "Setup a weekly briefing with Alice Vance next Monday at 9 AM",
    "Schedule conflict resolution with Globex Corp next Wednesday at 4 PM"
  ];

  const handlePlan = async (textToPlan = prompt) => {
    if (!textToPlan.trim()) return;
    setLoading(true);
    setScheduledEvent(null);
    try {
      const response = await api.post('/scheduler/plan', { request: textToPlan.trim() });
      setPlan(response.data);
      addToast('success', 'Plan Generated', 'Meeting details, availability, and email draft parsed successfully.');
    } catch (err: any) {
      console.error(err);
      const detail = err.response?.data?.detail || 'Parsing error.';
      addToast('error', 'Planning Failed', detail);
    } finally {
      setLoading(false);
    }
  };

  const handleSchedule = async () => {
    if (!plan) return;
    setScheduling(true);
    try {
      const response = await api.post('/scheduler/create', {
        title: plan.title,
        date: plan.date,
        time: plan.time,
        duration: plan.duration,
        timezone: plan.timezone,
        attendees: plan.attendees,
        email_draft: plan.email_draft
      });
      setScheduledEvent({
        event_id: response.data.event_id,
        meet_link: response.data.google_meet_link,
        calendar_url: response.data.calendar_url,
        meeting_id: response.data.meeting_id
      });
      addToast('success', 'Meeting Scheduled', 'Calendar event created with Google Meet link integration.');
    } catch (err: any) {
      console.error(err);
      addToast('error', 'Scheduling Failed', err.response?.data?.detail || 'Failed to create calendar event.');
    } finally {
      setScheduling(false);
    }
  };

  const handleSendInvites = async () => {
    if (!scheduledEvent || !scheduledEvent.meeting_id) return;
    setSendingInvites(true);
    try {
      await api.post('/scheduler/send-invites', {
        meeting_id: scheduledEvent.meeting_id
      });
      addToast('success', 'Invitations Sent', 'Gmail invitations dispatched to all attendees.');
      setPlan(null);
      setScheduledEvent(null);
      setPrompt('');
    } catch (err: any) {
      console.error(err);
      addToast('error', 'Dispatch Failed', err.response?.data?.detail || 'Failed to send invitations.');
    } finally {
      setSendingInvites(false);
    }
  };

  return (
    <main className="flex-1 p-5 xl:p-6 overflow-y-auto min-h-0 grid grid-cols-1 lg:grid-cols-5 gap-6">
      
      {/* Left Column: Natural language input and parameter breakdown */}
      <div className="lg:col-span-2 space-y-6 flex flex-col h-fit">
        
        {/* NLP Input Card */}
        <Card className="p-6 text-left space-y-5">
          <div className="flex items-center gap-2.5">
            <Sparkles className="text-indigo-400" size={18} />
            <h2 className="text-base font-bold text-slate-100 font-display">AI Meeting Planner</h2>
          </div>

          <p className="text-xs text-zinc-400 leading-relaxed">
            Enter a scheduling request in natural language. The AI will parse attendees, timings, and generate Gmail drafts.
          </p>

          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="e.g. Schedule a 45 min meeting with Alice Vance next Tuesday at 3 PM about prototype reviews"
            rows={4}
            className="w-full bg-zinc-950 border border-zinc-800 rounded-lg p-3 text-sm text-slate-100 placeholder-zinc-500 focus:outline-none focus:border-indigo-500 transition-all resize-none"
          />

          <Button variant="primary" fullWidth onClick={() => handlePlan()} disabled={loading || !prompt.trim()}>
            {loading ? (
              <>
                <Loader2 size={16} className="animate-spin mr-2" />
                Planning...
              </>
            ) : "Analyze & Check Availability"}
          </Button>

          {/* Quick Suggestions */}
          <div className="space-y-2">
            <h4 className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider">Example Templates</h4>
            <div className="flex flex-col gap-2">
              {suggestions.map((s, idx) => (
                <button
                  key={idx}
                  onClick={() => {
                    setPrompt(s);
                    handlePlan(s);
                  }}
                  className="text-left text-xs text-zinc-400 hover:text-indigo-400 p-2 bg-zinc-950/40 rounded border border-zinc-900 hover:border-indigo-500/30 transition-all cursor-pointer truncate"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        </Card>

        {/* Parsed meeting details card */}
        {plan && (
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
            <Card className="p-6 text-left space-y-4">
              <h3 className="text-sm font-bold text-slate-200 font-display border-b border-zinc-850 pb-2">
                Parsed Meeting Details
              </h3>
              
              <div className="space-y-3 text-xs">
                <div>
                  <span className="text-zinc-500 uppercase font-semibold">Title</span>
                  <p className="text-slate-200 font-bold text-sm mt-0.5">{plan.title}</p>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <span className="text-zinc-500 uppercase font-semibold">Date</span>
                    <p className="text-slate-200 font-bold mt-0.5">{plan.date}</p>
                  </div>
                  <div>
                    <span className="text-zinc-500 uppercase font-semibold">Time</span>
                    <p className="text-slate-200 font-bold mt-0.5">{plan.time}</p>
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <span className="text-zinc-500 uppercase font-semibold">Duration</span>
                    <p className="text-slate-200 font-bold mt-0.5">{plan.duration}</p>
                  </div>
                  <div>
                    <span className="text-zinc-500 uppercase font-semibold">Timezone</span>
                    <p className="text-slate-200 font-bold mt-0.5">{plan.timezone}</p>
                  </div>
                </div>
              </div>
            </Card>
          </motion.div>
        )}
      </div>

      {/* Right Column: Review resolves, Google Calendar status, draft email & schedule button */}
      <div className="lg:col-span-3 space-y-6">
        
        {loading ? (
          <div className="h-64 flex items-center justify-center bg-zinc-900 border border-zinc-800 rounded-xl">
            <LoadingSpinner size="md" />
          </div>
        ) : scheduledEvent ? (
          /* Scheduled Success View */
          <motion.div initial={{ opacity: 0, scale: 0.98 }} animate={{ opacity: 1, scale: 1 }}>
            <Card className="p-8 text-center space-y-6 border-emerald-500/20 bg-emerald-950/5">
              <div className="w-12 h-12 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 flex items-center justify-center mx-auto">
                <CalendarCheck size={24} />
              </div>

              <div>
                <h3 className="text-lg font-bold text-slate-100 font-display">Meeting Successfully Scheduled</h3>
                <p className="text-xs text-zinc-400 mt-1">Calendar event logged on Google Calendar</p>
              </div>

              {scheduledEvent.meet_link && (
                <div className="p-3 bg-zinc-950/60 rounded-lg border border-zinc-800 text-left max-w-sm mx-auto">
                  <span className="text-[10px] text-zinc-500 uppercase font-semibold">Google Meet Join URL</span>
                  <a
                    href={scheduledEvent.meet_link}
                    target="_blank"
                    rel="noreferrer"
                    className="text-xs font-bold text-indigo-400 hover:underline flex items-center gap-1.5 mt-1 overflow-hidden"
                  >
                    {scheduledEvent.meet_link}
                    <ExternalLink size={12} className="shrink-0" />
                  </a>
                </div>
              )}

              <div className="flex flex-col gap-3 max-w-xs mx-auto">
                <Button variant="accent" fullWidth onClick={handleSendInvites} disabled={sendingInvites}>
                  {sendingInvites ? "Sending invites..." : "Send Gmail invitations Now"}
                </Button>
                <Button
                  variant="secondary"
                  fullWidth
                  onClick={() => {
                    setPlan(null);
                    setScheduledEvent(null);
                    setPrompt('');
                  }}
                >
                  Schedule Another Meeting
                </Button>
              </div>
            </Card>
          </motion.div>
        ) : plan ? (
          /* Plan details & review card */
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="space-y-6 text-left">
            
            {/* Attendees Resolution Card */}
            <Card className="p-6 space-y-4">
              <h3 className="text-sm font-bold text-slate-200 font-display flex items-center gap-2">
                <UserCheck size={16} className="text-indigo-400" />
                Attendee Resolutions
              </h3>

              <div className="space-y-3">
                {plan.attendee_resolutions.map((res, idx) => {
                  const isAmbiguous = res.status === 'AMBIGUOUS';
                  const isNotFound = res.status === 'NOT_FOUND';
                  return (
                    <div key={idx} className="flex items-center justify-between p-3 bg-zinc-950/40 rounded-lg border border-zinc-800">
                      <div className="flex flex-col text-left">
                        <span className="text-xs font-bold text-slate-300">{res.input_name}</span>
                        <span className="text-[10px] text-zinc-500 mt-0.5">
                          {res.resolved_email || 'No email resolved'}
                        </span>
                      </div>
                      
                      <div className="flex items-center gap-2">
                        {isAmbiguous ? (
                          <Badge variant="warning">Ambiguous</Badge>
                        ) : isNotFound ? (
                          <Badge variant="danger">Not Found</Badge>
                        ) : (
                          <Badge variant="success">Resolved</Badge>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </Card>

            {/* Calendar Availability Status Card */}
            <Card className="p-6 space-y-4">
              <h3 className="text-sm font-bold text-slate-200 font-display flex items-center gap-2">
                <CalendarDays size={16} className="text-indigo-400" />
                Calendar Availability check
              </h3>

              {plan.calendar_preview.available ? (
                <div className="p-4 bg-emerald-500/5 border border-emerald-500/10 rounded-lg text-emerald-400 text-xs font-bold flex items-center gap-2">
                  <CalendarCheck size={16} />
                  Time slot is open! No calendar clashes detected.
                </div>
              ) : (
                <div className="space-y-3">
                  <div className="p-4 bg-red-500/5 border border-red-500/10 rounded-lg text-red-400 text-xs font-bold flex items-center gap-2">
                    <AlertTriangle size={16} />
                    Time slot Conflict! Existing calendar events found.
                  </div>
                  {plan.calendar_preview.conflicts.length > 0 && (
                    <div className="text-xs space-y-1">
                      <span className="text-zinc-500 font-semibold uppercase">Clashing Events:</span>
                      {plan.calendar_preview.conflicts.map((c, i) => (
                        <p key={i} className="text-zinc-400 font-mono">{c}</p>
                      ))}
                    </div>
                  )}
                  {plan.calendar_preview.suggestions.length > 0 && (
                    <div className="space-y-1.5 pt-2">
                      <span className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider">Suggested alternative slots</span>
                      <div className="flex flex-wrap gap-2">
                        {plan.calendar_preview.suggestions.map((slot, i) => (
                          <button
                            key={i}
                            onClick={() => {
                              // Slot typically comes in format "YYYY-MM-DD at HH:MM"
                              // We can update the text prompt to map to this alternative time
                              setPrompt(`Schedule a sync with Alice at ${slot}`);
                              handlePlan(`Schedule a sync with Alice at ${slot}`);
                            }}
                            className="px-2.5 py-1.5 rounded bg-zinc-900 border border-zinc-800 hover:border-indigo-500 text-zinc-300 hover:text-slate-100 text-xs cursor-pointer"
                          >
                            {slot}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </Card>

            {/* Email Draft Preview */}
            <Card className="p-6 space-y-4">
              <h3 className="text-sm font-bold text-slate-200 font-display flex items-center gap-2">
                <MailOpen size={16} className="text-indigo-400" />
                AI Generated Email Invitation
              </h3>
              
              <div className="p-4 bg-zinc-950/60 rounded-lg border border-zinc-800 text-xs text-zinc-400 leading-relaxed font-sans whitespace-pre-wrap max-h-48 overflow-y-auto">
                {plan.email_draft}
              </div>
            </Card>

            {/* Finalize Schedule Button */}
            <Button variant="accent" fullWidth onClick={handleSchedule} disabled={scheduling} className="py-3">
              {scheduling ? "Creating calendar event..." : "Log Meeting & Confirm Invite Draft"}
            </Button>

          </motion.div>
        ) : (
          <div className="h-full min-h-[300px] flex flex-col items-center justify-center text-center text-zinc-500 bg-zinc-900/30 border border-dashed border-zinc-800 rounded-xl p-8">
            <CalendarDays size={32} className="text-zinc-600 mb-3" />
            <span className="text-sm font-semibold">No plan loaded</span>
            <span className="text-xs text-zinc-500 mt-1 max-w-[240px]">Enter details on the left and run analysis to inspect conflicts and review drafts.</span>
          </div>
        )}

      </div>

    </main>
  );
};

export default SchedulerPage;

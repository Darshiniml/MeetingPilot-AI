import React, { useEffect, useState } from 'react';
import api from '../../services/api';
import {
  Sparkles,
  Play,
  CalendarRange,
  MessageSquare,
  History,
  Users,
  Video,
  Link,
  ChevronRight,
  TrendingUp,
  BrainCircuit
} from 'lucide-react';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { StatsCard } from '../../components/ui/StatsCard';
import { Badge } from '../../components/ui/Badge';
import { LoadingSpinner } from '../../components/ui/LoadingSpinner';

interface Meeting {
  id: number;
  title: string;
  date: string;
  duration?: number;
  transcript_count?: number;
  summary?: string;
}

interface DashboardHomeProps {
  onSelectView: (view: string) => void;
  onSelectMeeting: (meetingId: number) => void;
}

export const DashboardHome: React.FC<DashboardHomeProps> = ({ onSelectView, onSelectMeeting }) => {
  const [meetings, setMeetings] = useState<Meeting[]>([]);
  const [contactsCount, setContactsCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [googleEmail, setGoogleEmail] = useState('');
  const [googleConnected, setGoogleConnected] = useState(false);

  const fetchDashboardData = async () => {
    setLoading(true);
    try {
      // Get meetings
      const meetingsRes = await api.get('/meetings?offset=0&limit=5');
      setMeetings(meetingsRes.data.items || []);

      // Get contacts
      const contactsRes = await api.get('/contacts');
      setContactsCount(contactsRes.data.length || 0);

      // Get Google status
      const googleRes = await api.get('/integrations/google/status');
      setGoogleConnected(googleRes.data.is_connected);
      setGoogleEmail(googleRes.data.google_email || '');
    } catch (err) {
      console.error("Failed to load dashboard data:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const totalDurationMin = meetings.reduce((acc, curr) => acc + (curr.duration || 0), 0) / 60;

  // Mock list of today's items & AI suggestions for modern layout
  const insights = [
    { text: "Globex sync: Follow up on action items assigned to Bob.", priority: "high" },
    { text: "AI Scheduler: Alice and Charlie have overlapping slots next Tuesday at 3 PM.", priority: "medium" },
    { text: "OCR Log: Vision captured 4 key architecture diagrams in yesterday's sync.", priority: "low" }
  ];

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center py-20">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  return (
    <main className="flex-1 p-5 xl:p-6 overflow-y-auto min-h-0 space-y-6 text-left">
      
      {/* Greetings Block */}
      <div className="flex items-center justify-between border-b border-zinc-900 pb-4">
        <div>
          <h1 className="text-xl font-bold text-slate-100 font-display flex items-center gap-2">
            Welcome back to MeetingPilot
            <Sparkles className="text-indigo-400 animate-pulse" size={16} />
          </h1>
          <p className="text-xs text-zinc-400 mt-1">Review active pipeline status, upcoming slots, and AI action logs.</p>
        </div>
      </div>

      {/* Grid of Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
        <StatsCard title="Total Meetings Logged" value={meetings.length} trend="+12% this week" trendType="up" icon={History} />
        <StatsCard title="Capture Duration" value={`${totalDurationMin.toFixed(1)}m`} trend="hours saved" trendType="neutral" icon={TrendingUp} />
        <StatsCard title="Resolved Contacts" value={contactsCount} trend="synced database" trendType="up" icon={Users} />
        <StatsCard title="Google integrations" value={googleConnected ? "Synced" : "Offline"} trend={googleConnected ? googleEmail : "Connect in settings"} trendType={googleConnected ? 'up' : 'neutral'} icon={Link} />
      </div>

      {/* Two Column Layout */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        
        {/* Left Columns: Today's slots, Recent meetings */}
        <div className="xl:col-span-2 space-y-6">
          
          {/* Quick Action Controls */}
          <Card className="p-6">
            <h3 className="font-display font-bold text-sm tracking-wide text-zinc-400 uppercase mb-4">Quick actions</h3>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <Button variant="primary" size="md" onClick={() => onSelectView('Live Meeting')} className="gap-2 justify-start py-3">
                <Play size={16} fill="white" />
                Start Live Capture
              </Button>
              <Button variant="secondary" size="md" onClick={() => onSelectView('Scheduler')} className="gap-2 justify-start py-3">
                <CalendarRange size={16} className="text-indigo-400" />
                Schedule AI Meeting
              </Button>
              <Button variant="secondary" size="md" onClick={() => onSelectView('Meeting Chat')} className="gap-2 justify-start py-3">
                <MessageSquare size={16} className="text-violet-400" />
                Open AI Assistant
              </Button>
            </div>
          </Card>

          {/* Recent Meetings list */}
          <Card className="p-6">
            <div className="flex items-center justify-between mb-4 border-b border-zinc-900 pb-3">
              <h3 className="font-display font-bold text-sm tracking-wide text-zinc-400 uppercase">Recent Sessions</h3>
              <button onClick={() => onSelectView('Meeting History')} className="text-xs text-indigo-400 hover:underline flex items-center font-bold">
                View all history
                <ChevronRight size={14} />
              </button>
            </div>
            {meetings.length === 0 ? (
              <p className="text-sm text-zinc-500 py-4">No recent meetings recorded yet.</p>
            ) : (
              <div className="space-y-3">
                {meetings.map((meeting) => {
                  const formattedDate = meeting.date || (meeting as any).start_time 
                    ? new Date(meeting.date || (meeting as any).start_time).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
                    : 'Unknown Date';
                  return (
                    <div
                      key={meeting.id}
                      onClick={() => {
                        onSelectMeeting(meeting.id);
                        onSelectView('Meeting History');
                      }}
                      className="p-3 bg-zinc-950/40 rounded-xl border border-zinc-900/60 hover:bg-zinc-900/50 hover:border-zinc-800 transition-all flex items-center justify-between cursor-pointer"
                    >
                      <div className="flex items-center gap-3">
                        <div className="w-9 h-9 rounded-lg bg-zinc-900 flex items-center justify-center text-zinc-500 border border-zinc-800 shrink-0">
                          <Video size={16} />
                        </div>
                        <div className="flex flex-col text-left">
                          <span className="text-sm font-bold text-slate-200">{meeting.title} (ID: {meeting.id})</span>
                          <span className="text-[10px] text-zinc-500 mt-0.5">{formattedDate} · {meeting.transcript_count ?? 0} chunks</span>
                        </div>
                      </div>
                      {meeting.summary ? (
                        <Badge variant="success">Summary Ready</Badge>
                      ) : (
                        <Badge variant="secondary">Audio Captured</Badge>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </Card>
        </div>

        {/* Right Column: AI Insights, Action logs */}
        <div className="xl:col-span-1 space-y-6">
          {/* AI Insights Monitor */}
          <Card className="p-6">
            <div className="flex items-center gap-2 mb-4 border-b border-zinc-900 pb-3">
              <BrainCircuit className="text-indigo-400" size={16} />
              <h3 className="font-display font-bold text-sm tracking-wide text-zinc-400 uppercase">AI Copilot Insights</h3>
            </div>
            
            <div className="space-y-3">
              {insights.map((ins, idx) => (
                <div key={idx} className="p-3 rounded-lg bg-zinc-950/60 border border-zinc-900 text-left text-xs leading-relaxed text-zinc-400">
                  <div className="flex items-center gap-1.5 mb-1.5">
                    {ins.priority === 'high' ? (
                      <Badge variant="danger">Action Required</Badge>
                    ) : ins.priority === 'medium' ? (
                      <Badge variant="warning">Alert</Badge>
                    ) : (
                      <Badge variant="info">OCR Log</Badge>
                    )}
                  </div>
                  {ins.text}
                </div>
              ))}
            </div>
          </Card>

          {/* Connected state reminder */}
          {!googleConnected && (
            <Card className="p-5 text-left border-indigo-500/20 bg-indigo-950/5 relative overflow-hidden">
              <div className="relative z-10 space-y-3">
                <h4 className="text-sm font-bold text-indigo-400">Connect Google Workspace</h4>
                <p className="text-[11px] text-zinc-400 leading-relaxed">
                  Authorize Calendar feeds and Gmail drafts to auto-synchronize schedules and trigger invite notifications automatically.
                </p>
                <Button variant="glass" size="sm" onClick={() => onSelectView('Settings')} className="text-[11px]">
                  Open settings
                </Button>
              </div>
              <div className="absolute right-0 bottom-0 opacity-10 translate-y-2 translate-x-2">
                <CalendarRange size={120} />
              </div>
            </Card>
          )}
        </div>

      </div>

    </main>
  );
};

export default DashboardHome;

import React, { useEffect, useState } from 'react';
import api from '../../services/api';
import { motion, AnimatePresence } from 'framer-motion';
import {
  User,
  Globe,
  Bell,
  Database,
  ExternalLink,
  CheckCircle2,
  AlertTriangle
} from 'lucide-react';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { Input } from '../../components/ui/Input';
import { Badge } from '../../components/ui/Badge';
import { useToastStore } from '../../store/useToastStore';
import { useAuth } from '../../context/AuthContext';

export const SettingsPage: React.FC = () => {
  const [activeSubTab, setActiveSubTab] = useState<'profile' | 'integrations' | 'notifications' | 'database'>('profile');
  const [googleConnected, setGoogleConnected] = useState(false);
  const [googleEmail, setGoogleEmail] = useState('');
  const [googleScopes, setGoogleScopes] = useState<string[]>([]);
  const [disconnecting, setDisconnecting] = useState(false);
  
  const { user } = useAuth();
  const { addToast } = useToastStore();

  const fetchGoogleStatus = async () => {
    try {
      const response = await api.get('/integrations/google/status');
      setGoogleConnected(response.data.is_connected);
      setGoogleEmail(response.data.google_email || '');
      setGoogleScopes(response.data.scopes || []);
    } catch (err) {
      console.error("Failed to load Google status in settings:", err);
    }
  };

  useEffect(() => {
    fetchGoogleStatus();
  }, []);

  const handleConnectGoogle = async () => {
    const token = localStorage.getItem("accessToken");
    if (!token) {
      addToast('error', 'Auth Failed', 'No active user session found.');
      return;
    }
    try {
      const response = await api.get(`/integrations/google/auth-url?token=${token}`);
      if (response.data.url) {
        window.location.href = response.data.url;
      }
    } catch (err) {
      console.error(err);
      addToast('error', 'OAuth Failed', 'Could not generate Google authorization link.');
    }
  };

  const handleDisconnectGoogle = async () => {
    if (!window.confirm("Are you sure you want to disconnect Google services? This will disable calendar sync and email delivery.")) return;
    setDisconnecting(true);
    try {
      await api.post('/integrations/google/disconnect');
      setGoogleConnected(false);
      setGoogleEmail('');
      setGoogleScopes([]);
      addToast('success', 'Disconnected', 'Google Calendar, Gmail, and Contacts connections cleared.');
    } catch (err) {
      console.error(err);
      addToast('error', 'Disconnect Failed', 'Could not disconnect account.');
    } finally {
      setDisconnecting(false);
    }
  };

  return (
    <main className="flex-1 p-5 xl:p-6 overflow-y-auto min-h-0 flex flex-col md:flex-row gap-6 text-left">
      
      {/* Left Column: Sub Tabs */}
      <div className="w-full md:w-64 space-y-1.5 shrink-0">
        <h2 className="font-display font-bold text-sm tracking-wide text-zinc-400 uppercase px-3 mb-3">Settings</h2>
        
        <button
          onClick={() => setActiveSubTab('profile')}
          className={`w-full text-left px-3 py-2.5 rounded-lg text-sm font-semibold flex items-center gap-3 transition-colors cursor-pointer ${
            activeSubTab === 'profile' ? 'bg-zinc-800 text-slate-100 border border-zinc-700/50' : 'text-zinc-400 hover:bg-zinc-900 hover:text-slate-100'
          }`}
        >
          <User size={16} />
          Account Profile
        </button>

        <button
          onClick={() => setActiveSubTab('integrations')}
          className={`w-full text-left px-3 py-2.5 rounded-lg text-sm font-semibold flex items-center gap-3 transition-colors cursor-pointer ${
            activeSubTab === 'integrations' ? 'bg-zinc-800 text-slate-100 border border-zinc-700/50' : 'text-zinc-400 hover:bg-zinc-900 hover:text-slate-100'
          }`}
        >
          <Globe size={16} />
          Integrations (Google)
        </button>

        <button
          onClick={() => setActiveSubTab('notifications')}
          className={`w-full text-left px-3 py-2.5 rounded-lg text-sm font-semibold flex items-center gap-3 transition-colors cursor-pointer ${
            activeSubTab === 'notifications' ? 'bg-zinc-800 text-slate-100 border border-zinc-700/50' : 'text-zinc-400 hover:bg-zinc-900 hover:text-slate-100'
          }`}
        >
          <Bell size={16} />
          Notifications
        </button>

        <button
          onClick={() => setActiveSubTab('database')}
          className={`w-full text-left px-3 py-2.5 rounded-lg text-sm font-semibold flex items-center gap-3 transition-colors cursor-pointer ${
            activeSubTab === 'database' ? 'bg-zinc-800 text-slate-100 border border-zinc-700/50' : 'text-zinc-400 hover:bg-zinc-900 hover:text-slate-100'
          }`}
        >
          <Database size={16} />
          System Settings
        </button>
      </div>

      {/* Right Column: Panel Contents */}
      <div className="flex-1 max-w-2xl">
        <Card className="p-6">
          <AnimatePresence mode="wait">
            {activeSubTab === 'profile' && (
              <motion.div
                key="profile"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                transition={{ duration: 0.15 }}
                className="space-y-6"
              >
                <div>
                  <h3 className="text-base font-bold text-slate-200 font-display">Account Profile</h3>
                  <p className="text-xs text-zinc-500 mt-1">Manage personal contact card and profile details.</p>
                </div>
                
                <div className="space-y-4">
                  <Input label="Profile Name" value={user?.name || 'User'} readOnly className="opacity-80 cursor-not-allowed bg-zinc-900" />
                  <Input label="Email address" value={user?.email || 'user@example.com'} readOnly className="opacity-80 cursor-not-allowed bg-zinc-900" />
                </div>
              </motion.div>
            )}

            {activeSubTab === 'integrations' && (
              <motion.div
                key="integrations"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className="space-y-6"
              >
                <div>
                  <h3 className="text-base font-bold text-slate-200 font-display">Integrations & Connected Apps</h3>
                  <p className="text-xs text-zinc-500 mt-1">Authorize Google Calendar, Gmail Send, and Contacts read access.</p>
                </div>

                {googleConnected ? (
                  /* Connected Status View */
                  <div className="space-y-4">
                    <div className="p-4 bg-emerald-500/5 border border-emerald-500/10 rounded-xl flex items-start gap-3">
                      <CheckCircle2 className="text-emerald-400 mt-0.5" size={20} />
                      <div className="flex-1 text-left">
                        <h4 className="text-sm font-bold text-slate-200">Google Workspace Synced</h4>
                        <p className="text-xs text-zinc-400 mt-1">
                          Connected as <span className="text-emerald-400 font-mono font-bold">{googleEmail}</span>. All calendar synchronizations, automatic Gmail invitation drafts, and Google Contacts read intelligence are actively running.
                        </p>
                      </div>
                    </div>

                    {googleScopes.length > 0 && (
                      <div className="space-y-2">
                        <h4 className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider">Authorized OAuth Scopes</h4>
                        <div className="flex flex-wrap gap-1.5">
                          {googleScopes.map((scope, idx) => (
                            <Badge key={idx} variant="primary" className="font-mono text-[9px] lowercase tracking-normal">
                              {scope.split('/').pop()}
                            </Badge>
                          ))}
                        </div>
                      </div>
                    )}

                    <div className="pt-4 border-t border-zinc-800">
                      <Button variant="danger" size="sm" onClick={handleDisconnectGoogle} disabled={disconnecting}>
                        Disconnect Google Account
                      </Button>
                    </div>
                  </div>
                ) : (
                  /* Disconnected View */
                  <div className="space-y-5">
                    <div className="p-4 bg-amber-500/5 border border-amber-500/10 rounded-xl flex items-start gap-3">
                      <AlertTriangle className="text-amber-400 mt-0.5" size={20} />
                      <div className="flex-1 text-left">
                        <h4 className="text-sm font-bold text-slate-200">Google Workspace Missing</h4>
                        <p className="text-xs text-zinc-400 mt-1">
                          Please authorize Google OAuth to connect Calendar, Gmail templates, and Contacts import pipelines.
                        </p>
                      </div>
                    </div>

                    <div className="space-y-3 bg-zinc-950/40 border border-zinc-900 rounded-xl p-4 text-xs text-zinc-400 leading-relaxed">
                      <h4 className="font-semibold text-slate-300">Authorized Capabilities:</h4>
                      <ul className="list-disc pl-4 space-y-1.5">
                        <li>Read and edit Google Calendar schedules.</li>
                        <li>Send AI-generated invitations from Gmail Send provider.</li>
                        <li>Read Google Contacts directories and merge changes.</li>
                      </ul>
                    </div>

                    <Button variant="primary" onClick={handleConnectGoogle} className="gap-2">
                      Connect Google Account
                      <ExternalLink size={14} />
                    </Button>
                  </div>
                )}
              </motion.div>
            )}

            {activeSubTab === 'notifications' && (
              <motion.div
                key="notifications"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className="space-y-6"
              >
                <div>
                  <h3 className="text-base font-bold text-slate-200 font-display">Notification Settings</h3>
                  <p className="text-xs text-zinc-500 mt-1">Manage processing updates, digest options, and browser toasts.</p>
                </div>

                <div className="space-y-4">
                  <div className="flex items-center justify-between p-3 bg-zinc-950/20 border border-zinc-900 rounded-lg">
                    <div>
                      <h4 className="text-sm font-bold text-slate-200">Toast Notifications</h4>
                      <p className="text-[10px] text-zinc-500 mt-0.5">Show overlay alerts for completed processes.</p>
                    </div>
                    <input type="checkbox" defaultChecked className="rounded border-zinc-800 text-indigo-600 focus:ring-indigo-500" />
                  </div>

                  <div className="flex items-center justify-between p-3 bg-zinc-950/20 border border-zinc-900 rounded-lg">
                    <div>
                      <h4 className="text-sm font-bold text-slate-200">Meeting summary emails</h4>
                      <p className="text-[10px] text-zinc-500 mt-0.5">Auto send meeting action lists to my email.</p>
                    </div>
                    <input type="checkbox" defaultChecked className="rounded border-zinc-800 text-indigo-600 focus:ring-indigo-500" />
                  </div>
                </div>
              </motion.div>
            )}

            {activeSubTab === 'database' && (
              <motion.div
                key="database"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className="space-y-6"
              >
                <div>
                  <h3 className="text-base font-bold text-slate-200 font-display">System Settings</h3>
                  <p className="text-xs text-zinc-500 mt-1">Verify backend connections, local AI pipelines, and database state.</p>
                </div>

                <div className="space-y-3 text-xs">
                  <div className="flex items-center justify-between p-3 border border-zinc-900 rounded-lg">
                    <span className="font-semibold text-zinc-400">Database Engine</span>
                    <span className="font-mono text-slate-300 font-bold bg-zinc-800 px-1.5 py-0.5 rounded border border-zinc-700">SQLite 3</span>
                  </div>
                  <div className="flex items-center justify-between p-3 border border-zinc-900 rounded-lg">
                    <span className="font-semibold text-zinc-400">AI Integration model</span>
                    <span className="font-mono text-indigo-400 font-bold bg-indigo-500/10 px-1.5 py-0.5 rounded border border-indigo-500/20">Gemini Pro API / Local Ollama</span>
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </Card>
      </div>

    </main>
  );
};

export default SettingsPage;

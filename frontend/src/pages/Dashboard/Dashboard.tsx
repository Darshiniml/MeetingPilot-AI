import { useState } from "react";
import api from "../../services/api";
import type { MeetingDetail } from "../../types/meeting";
import Sidebar from "../../components/layout/Sidebar";
import Header from "../../components/layout/Header";
import LiveMeetingPage from "../LiveMeeting/LiveMeetingPage";
import MeetingChat from "../MeetingChat/MeetingChat";
import ContactsPage from "../Contacts/ContactsPage";
import SchedulerPage from "../Scheduler/SchedulerPage";
import SettingsPage from "../Settings/SettingsPage";
import DashboardHome from "./DashboardHome";
import WorkflowCenter from "../Workflows/WorkflowCenter";
import AgentCenter from "../Agents/AgentCenter";
import MCPCenter from "../MCP/MCPCenter";
import A2ACenter from "../A2A/A2ACenter";
import ApprovalCenter from "../Approvals/ApprovalCenter";
import AgentControlCenterPage from "../AgentControlCenter/AgentControlCenterPage";

// History components
import MeetingHistoryPanel from "../../components/history/MeetingHistoryPanel";
import MeetingDetailPanel from "../../components/history/MeetingDetailPanel";
import MeetingStatsPanel from "../../components/history/MeetingStatsPanel";
import SummaryPanel from "../../components/summary/SummaryPanel";
import TaskPanel from "../../components/tasks/TaskPanel";
import ChatPanel from "../../components/chat/ChatPanel";

// Global overlay components
import { Toaster } from "../../components/ui/Toast";
import { CommandPalette } from "../../components/layout/CommandPalette";
import { useToastStore } from "../../store/useToastStore";

function Dashboard() {
  const [activeView, setActiveView] = useState("Dashboard");
  const [meeting, setMeeting] = useState<MeetingDetail | null>(null);
  const { addToast } = useToastStore();

  const loadMeeting = async (meetingId: number) => {
    try {
      const response = await api.get(`/meetings/${meetingId}`);
      setMeeting(response.data);
    } catch (error) {
      console.error(error);
      addToast('error', 'Error Loading', 'Failed to retrieve meeting details.');
    }
  };

  const selectHistoryMeeting = async (meetingId: number) => {
    await loadMeeting(meetingId);
    setActiveView("Meeting History");
  };

  const handleTriggerSync = async () => {
    try {
      addToast('info', 'Sync Started', 'Synchronizing with Google Contacts API...');
      await api.post('/contacts/import', { provider: 'google' });
      addToast('success', 'Sync Finished', `Imported contacts database.`);
    } catch (err) {
      addToast('error', 'Sync Failed', 'Could not sync Google Contacts.');
    }
  };

  return (
    <div className="flex min-h-screen bg-bg-dark text-slate-100 overflow-hidden font-sans">
      {/* Toast Overlay notifications */}
      <Toaster />

      {/* Command Palette Ctrl+K search */}
      <CommandPalette
        onSelectView={setActiveView}
        onTriggerSync={handleTriggerSync}
      />

      <Sidebar activeView={activeView} onSelectView={setActiveView} />

      <div className="flex-1 flex flex-col min-h-screen overflow-hidden">
        <Header
          title={activeView}
          onOpenSearch={() => {
            // Trigger Ctrl+K window programmatically by dispatching a KeyboardEvent
            const event = new KeyboardEvent('keydown', {
              key: 'k',
              ctrlKey: true,
              bubbles: true
            });
            window.dispatchEvent(event);
          }}
        />

        {/* View Switcher Routing */}
        <div className="flex-1 flex flex-col min-h-0 overflow-y-auto">
          {activeView === "Dashboard" && (
            <DashboardHome onSelectView={setActiveView} onSelectMeeting={selectHistoryMeeting} />
          )}

          {activeView === "Live Meeting" && (
            <LiveMeetingPage onMeetingStopped={selectHistoryMeeting} />
          )}

          {activeView === "Meeting Chat" && (
            <MeetingChat />
          )}

          {activeView === "Scheduler" && (
            <SchedulerPage />
          )}

          {activeView === "Contacts" && (
            <ContactsPage />
          )}

          {activeView === "Settings" && (
            <SettingsPage />
          )}

          {activeView === "Workflows" && (
            <WorkflowCenter />
          )}

          {activeView === "Agents" && (
            <AgentCenter />
          )}

          {activeView === "MCP" && (
            <MCPCenter />
          )}

          {activeView === "A2A" && (
            <A2ACenter />
          )}

          {activeView === "Approvals" && (
            <ApprovalCenter />
          )}

          {activeView === "Agent Control Center" && (
            <AgentControlCenterPage />
          )}

          {activeView === "Meeting History" && (
            <main className="grid flex-1 grid-cols-1 gap-6 p-5 xl:grid-cols-3 xl:p-6 min-h-0">
              <div className="xl:col-span-1 min-h-0 overflow-y-auto">
                <MeetingHistoryPanel selectedMeetingId={meeting?.id ?? null} onSelectMeeting={selectHistoryMeeting} />
              </div>
              <div className="space-y-6 xl:col-span-2 min-h-0 overflow-y-auto pr-2 pb-6">
                <MeetingDetailPanel meeting={meeting} />
                <MeetingStatsPanel meeting={meeting} />
                <SummaryPanel content={meeting?.summary ?? null} />
                <TaskPanel items={meeting?.action_items ?? []} />
                <ChatPanel meetingId={meeting?.id ?? null} />
              </div>
            </main>
          )}
        </div>
      </div>
    </div>
  );
}

export default Dashboard;

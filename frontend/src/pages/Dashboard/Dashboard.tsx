import Sidebar from "../../components/layout/Sidebar";
import Header from "../../components/layout/Header";
import TranscriptPanel from "../../components/transcript/TranscriptPanel";
import SummaryPanel from "../../components/summary/SummaryPanel";
import TaskPanel from "../../components/tasks/TaskPanel";
import ChatPanel from "../../components/chat/ChatPanel";

function Dashboard() {
  return (
    <div className="flex min-h-screen bg-slate-950 text-white">
      <Sidebar />

      <div className="flex-1 flex flex-col">
        <Header />

        <main className="flex-1 grid grid-cols-3 gap-6 p-6">
          <div className="col-span-2">
            <TranscriptPanel />
          </div>

          <div className="space-y-6">
            <SummaryPanel />
            <TaskPanel />
            <ChatPanel />
          </div>
        </main>
      </div>
    </div>
  );
}

export default Dashboard;
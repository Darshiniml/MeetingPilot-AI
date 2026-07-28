const menuItems = [
  "Dashboard",
  "Live Meeting",
  "Meeting History",
  "Tasks",
  "Reports",
  "Settings",
];

function Sidebar() {
  return (
    <aside className="w-64 h-screen bg-slate-900 border-r border-slate-800 p-6">
      <h1 className="text-2xl font-bold text-white mb-10">
        🧠 MeetingPilot AI
      </h1>

      <nav className="space-y-3">
        {menuItems.map((item) => (
          <button
            key={item}
            className="w-full text-left px-4 py-3 rounded-lg text-slate-300 hover:bg-slate-800 hover:text-white transition"
          >
            {item}
          </button>
        ))}
      </nav>
    </aside>
  );
}

export default Sidebar;
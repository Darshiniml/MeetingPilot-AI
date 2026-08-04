import type { ActionItem } from "../../types/meeting";
import { CheckSquare } from "lucide-react";
import { Card } from "../ui/Card";
import { Badge } from "../ui/Badge";

type TaskPanelProps = { items: ActionItem[] };

function TaskPanel({ items }: TaskPanelProps) {
  if (items.length === 0) return null;

  return (
    <Card hoverEffect={false} className="p-6 text-left">
      <div className="flex items-center gap-2 mb-4 border-b border-zinc-900 pb-3">
        <CheckSquare className="text-indigo-400" size={16} />
        <h2 className="text-sm font-bold text-slate-200 font-display">Action Items</h2>
      </div>

      <div className="space-y-2">
        {items.map((item) => (
          <div
            key={item.id}
            className="p-3.5 bg-zinc-950/40 rounded-xl border border-zinc-900 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-left"
          >
            <div className="flex flex-col text-left">
              <span className="text-xs font-bold text-slate-200 leading-relaxed font-sans">{item.task}</span>
              <span className="text-[10px] text-zinc-500 mt-1">
                Assignee: <span className="text-zinc-400 font-bold">{item.owner || "Unassigned"}</span>
              </span>
            </div>
            
            <div className="flex items-center gap-2 self-start sm:self-center">
              {item.due_date && (
                <span className="text-[9px] font-mono text-zinc-500 bg-zinc-900 border border-zinc-800 px-1.5 py-0.5 rounded">
                  Due {item.due_date.slice(0, 10)}
                </span>
              )}
              <Badge variant={item.priority === 'high' ? 'danger' : item.priority === 'medium' ? 'warning' : 'info'}>
                {item.priority || 'no priority'}
              </Badge>
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}

export default TaskPanel;

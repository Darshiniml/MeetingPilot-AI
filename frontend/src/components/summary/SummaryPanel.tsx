import { useState } from "react";
import { Download, BrainCircuit, Copy, Check } from "lucide-react";
import { Card } from "../ui/Card";
import { Button } from "../ui/Button";

type SummaryPanelProps = { content: string | null };

function SummaryPanel({ content }: SummaryPanelProps) {
  const [copied, setCopied] = useState(false);

  if (!content) return null;

  const download = () => {
    const link = document.createElement("a");
    link.href = URL.createObjectURL(new Blob([content], { type: "text/plain" }));
    link.download = "meeting-summary.txt";
    link.click();
    URL.revokeObjectURL(link.href);
  };

  const copy = () => {
    navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <Card hoverEffect={false} className="p-6 text-left">
      <div className="flex items-center justify-between border-b border-zinc-900 pb-4 mb-4 gap-2">
        <div className="flex items-center gap-2">
          <BrainCircuit className="text-indigo-400" size={16} />
          <h2 className="text-sm font-bold text-slate-200 font-display">AI Summary</h2>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="secondary" size="sm" onClick={copy} className="gap-1 text-xs py-1 px-2.5">
            {copied ? <Check size={12} className="text-emerald-400" /> : <Copy size={12} />}
            Copy
          </Button>
          <Button variant="secondary" size="sm" onClick={download} className="gap-1 text-xs py-1 px-2.5">
            <Download size={12} />
            Download
          </Button>
        </div>
      </div>
      <p className="whitespace-pre-wrap text-zinc-400 text-xs leading-relaxed font-sans">{content}</p>
    </Card>
  );
}

export default SummaryPanel;

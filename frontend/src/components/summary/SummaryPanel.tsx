type SummaryPanelProps = {
  content: string | null;
};

function SummaryPanel({ content }: SummaryPanelProps) {
  return (
    <div className="bg-slate-900 rounded-xl p-6">
      <h2 className="text-xl font-semibold mb-4">
        📝 AI Summary
      </h2>

      <p className="whitespace-pre-wrap text-slate-400">
        {content ?? "No summary available."}
      </p>
    </div>
  );
}

export default SummaryPanel;

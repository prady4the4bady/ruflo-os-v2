import { useEffect, useState } from "react";

type FirstBootWizardProps = {
  open: boolean;
  onClose: () => void;
};

export default function FirstBootWizard({ open, onClose }: FirstBootWizardProps): JSX.Element | null {
  const [completing, setCompleting] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string>("");

  useEffect(() => {
    if (!open) {
      setStatusMessage("");
    }
  }, [open]);

  if (!open) {
    return null;
  }

  async function markComplete(): Promise<void> {
    setCompleting(true);
    setStatusMessage("");
    try {
      const response = await fetch("/api/system/first-boot-complete", { method: "POST" });
      if (!response.ok) {
        throw new Error("Failed to complete first boot");
      }
      setStatusMessage("First boot marked complete.");
      onClose();
    } catch {
      setStatusMessage("Unable to mark first boot complete. Please try again.");
    } finally {
      setCompleting(false);
    }
  }

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.45)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 75,
      }}
    >
      <div
        style={{
          width: "min(1120px, 94vw)",
          height: "min(780px, 92vh)",
          borderRadius: 18,
          overflow: "hidden",
          border: "1px solid rgba(58,58,60,0.6)",
          background: "#0a0e1a",
          display: "flex",
          flexDirection: "column",
        }}
      >
        <div
          style={{
            height: 46,
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            padding: "0 14px",
            background: "rgba(17,24,39,0.88)",
            color: "#F9FAFB",
          }}
        >
          <strong>PradyOS First Boot Wizard</strong>
          <div style={{ display: "flex", gap: 8 }}>
            <button
              type="button"
              onClick={() => {
                void markComplete();
              }}
              disabled={completing}
              style={{
                borderRadius: 8,
                border: "1px solid rgba(16,185,129,0.6)",
                background: "rgba(16,185,129,0.25)",
                color: "#D1FAE5",
                padding: "5px 10px",
                cursor: completing ? "default" : "pointer",
              }}
            >
              {completing ? "Completing..." : "Mark Complete"}
            </button>
            <button
              type="button"
              onClick={onClose}
              style={{
                borderRadius: 8,
                border: "1px solid rgba(148,163,184,0.4)",
                background: "transparent",
                color: "#E5E7EB",
                padding: "5px 10px",
                cursor: "pointer",
              }}
            >
              Close
            </button>
          </div>
        </div>
        {statusMessage ? (
          <div
            style={{
              padding: "8px 12px",
              fontSize: 13,
              color: "#E5E7EB",
              background: "rgba(31,41,55,0.9)",
            }}
          >
            {statusMessage}
          </div>
        ) : null}
        <iframe title="PradyOS First Boot Wizard" src="http://localhost:8099/oobe" style={{ flex: 1, border: 0, width: "100%" }} />
      </div>
    </div>
  );
}

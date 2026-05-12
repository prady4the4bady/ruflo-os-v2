type AboutData = {
  name: string;
  version: string;
  channel: string;
  build?: string;
};

type AboutProps = {
  open: boolean;
  onClose: () => void;
  about: AboutData;
};

export default function About({ open, onClose, about }: AboutProps): JSX.Element | null {
  if (!open) {
    return null;
  }

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.42)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 70,
      }}
      onClick={onClose}
    >
      <section
        style={{
          width: 420,
          borderRadius: 16,
          border: "1px solid rgba(58,58,60,0.5)",
          background: "rgba(28,28,30,0.9)",
          color: "#F2F2F7",
          padding: 20,
          backdropFilter: "blur(12px)",
          WebkitBackdropFilter: "blur(12px)",
        }}
        onClick={(event) => event.stopPropagation()}
      >
        <h2 style={{ margin: 0, fontSize: 20 }}>About PradyOS</h2>
        <p style={{ marginTop: 8, color: "#AEAEB2" }}>
          Version {about.version} · Channel {about.channel}
        </p>
        <p style={{ marginTop: 8, color: "#D1D1D6", fontSize: 13 }}>Build {about.build ?? "unknown"}</p>
        <p style={{ marginTop: 12, color: "#D1D1D6", fontSize: 13 }}>{about.name} desktop shell and AI platform runtime.</p>
        <button
          type="button"
          onClick={onClose}
          style={{
            marginTop: 12,
            borderRadius: 10,
            border: "1px solid rgba(118,118,128,0.4)",
            background: "rgba(99,102,241,0.85)",
            color: "#fff",
            padding: "6px 12px",
            cursor: "pointer",
          }}
        >
          Close
        </button>
      </section>
    </div>
  );
}

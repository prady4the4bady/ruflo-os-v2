import { invoke } from "@tauri-apps/api/core";
import type { DockAppConfig } from "../../types";

interface Props {
  app: DockAppConfig;
  bouncing: boolean;
  onLaunch: (app: DockAppConfig) => void;
}

export default function DockItem({ app, bouncing, onLaunch }: Props) {
  const handleClick = () => {
    onLaunch(app);
    invoke("launch_dock_app", { app: app.id }).catch((err) => {
      console.error(`Failed to launch ${app.label}:`, err);
    });
  };

  return (
    <div
      role="button"
      aria-label={`Launch ${app.label}`}
      className={`dock-item${bouncing ? " dock-item--bouncing" : ""}`}
      onClick={handleClick}
      onKeyDown={(e) => e.key === "Enter" && handleClick()}
      tabIndex={0}
    >
      <div className="dock-item__icon">{app.icon}</div>
      <span className="dock-item__label">{app.label}</span>
    </div>
  );
}

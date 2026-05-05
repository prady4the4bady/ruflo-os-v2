import Clock from "./Clock";
import AiStatus from "./AiStatus";
import SystemIndicators from "./SystemIndicators";

export default function MenuBar() {
  return (
    <nav className="menubar glass">
      <div className="menubar__left">
        <AiStatus />
      </div>
      <div className="menubar__right">
        <SystemIndicators />
        <Clock />
      </div>
    </nav>
  );
}

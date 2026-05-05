/** Placeholder Wi-Fi and battery indicators.
 *  On Linux there is no standard Web API for these; reading them requires
 *  native polling (future Tauri command). For now we render static SVG icons
 *  that can be wired up later. */
export default function SystemIndicators() {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13 }}>
      {/* Wi-Fi icon */}
      <span title="Wi-Fi">
        <svg width="16" height="12" viewBox="0 0 16 12" fill="currentColor">
          <path d="M8 9.5a1.5 1.5 0 1 1 0 3 1.5 1.5 0 0 1 0-3zm0-3.5a5.5 5.5 0 0 1 3.9 1.61l-1.06 1.06A4 4 0 0 0 8 7.5a4 4 0 0 0-2.84 1.17L4.1 7.61A5.5 5.5 0 0 1 8 6zm0-3.5A9 9 0 0 1 14.24 4.9L13.18 5.96A7.5 7.5 0 0 0 8 4a7.5 7.5 0 0 0-5.18 1.96L1.76 4.9A9 9 0 0 1 8 2.5z"/>
        </svg>
      </span>
      {/* Battery icon */}
      <span title="Battery">
        <svg width="20" height="12" viewBox="0 0 20 12" fill="currentColor">
          <rect x="1" y="1" width="15" height="10" rx="2" ry="2" stroke="currentColor" strokeWidth="1.5" fill="none"/>
          <rect x="16" y="3.5" width="3" height="5" rx="1.5" ry="1.5"/>
          <rect x="2.5" y="2.5" width="11" height="7" rx="1" ry="1" opacity="0.7"/>
        </svg>
      </span>
    </div>
  );
}

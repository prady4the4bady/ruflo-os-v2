use serde::{Deserialize, Serialize};

// ── App identifiers ─────────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum DockApp {
    Terminal,
    Files,
    Browser,
    PradyTasks,
    Settings,
}

// ── Pure functions (testable) ───────────────────────────────────────────────

/// Returns [program, arg1, arg2, ...] for `sh -c "<fallback-chain>"`.
pub fn get_launch_command(app: &DockApp) -> Vec<String> {
    let sh_c = |cmd: &str| vec!["sh".to_string(), "-c".to_string(), cmd.to_string()];
    match app {
        DockApp::Terminal => sh_c("kitty 2>/dev/null || xterm"),
        DockApp::Files => sh_c("nautilus 2>/dev/null || thunar"),
        DockApp::Browser => {
            sh_c("firefox 2>/dev/null || chromium 2>/dev/null || chromium-browser")
        }
        DockApp::PradyTasks => {
            let port = std::env::var("WORKFLOW_ENGINE_PORT")
                .unwrap_or_else(|_| "8001".to_string());
            sh_c(&format!(
                "xdg-open http://localhost:{port} 2>/dev/null \
                 || firefox http://localhost:{port}"
            ))
        }
        DockApp::Settings => {
            sh_c("gnome-control-center 2>/dev/null || xfce4-settings-manager 2>/dev/null || true")
        }
    }
}

pub fn app_display_name(app: &DockApp) -> &'static str {
    match app {
        DockApp::Terminal => "Terminal",
        DockApp::Files => "Files",
        DockApp::Browser => "Browser",
        DockApp::PradyTasks => "Prady Tasks",
        DockApp::Settings => "Settings",
    }
}

pub fn app_icon_name(app: &DockApp) -> &'static str {
    match app {
        DockApp::Terminal => "🖥️",
        DockApp::Files => "📁",
        DockApp::Browser => "🌐",
        DockApp::PradyTasks => "🤖",
        DockApp::Settings => "⚙️",
    }
}

/// All default dock apps, in display order.
pub fn default_dock_apps() -> Vec<DockApp> {
    vec![
        DockApp::Terminal,
        DockApp::Files,
        DockApp::Browser,
        DockApp::PradyTasks,
        DockApp::Settings,
    ]
}

// ── Unit tests ──────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn terminal_uses_sh_with_kitty_fallback() {
        let cmd = get_launch_command(&DockApp::Terminal);
        assert_eq!(cmd[0], "sh");
        assert_eq!(cmd[1], "-c");
        assert!(cmd[2].contains("kitty"), "should prefer kitty");
        assert!(cmd[2].contains("xterm"), "should fallback to xterm");
    }

    #[test]
    fn files_uses_nautilus_with_thunar_fallback() {
        let cmd = get_launch_command(&DockApp::Files);
        assert!(cmd[2].contains("nautilus"));
        assert!(cmd[2].contains("thunar"));
    }

    #[test]
    fn browser_has_three_tier_fallback() {
        let cmd = get_launch_command(&DockApp::Browser);
        assert!(cmd[2].contains("firefox"));
        assert!(cmd[2].contains("chromium"));
    }

    #[test]
    fn prady_tasks_opens_localhost_url() {
        let cmd = get_launch_command(&DockApp::PradyTasks);
        assert!(cmd[2].contains("localhost"));
        assert!(cmd[2].contains("http"));
    }

    #[test]
    fn all_display_names_are_non_empty() {
        for app in default_dock_apps() {
            assert!(!app_display_name(&app).is_empty());
        }
    }

    #[test]
    fn default_dock_has_five_apps() {
        assert_eq!(default_dock_apps().len(), 5);
    }

    #[test]
    fn dock_app_roundtrip_json() {
        let app = DockApp::PradyTasks;
        let json = serde_json::to_string(&app).unwrap();
        assert_eq!(json, r#""prady_tasks""#);
        let back: DockApp = serde_json::from_str(&json).unwrap();
        assert!(matches!(back, DockApp::PradyTasks));
    }
}

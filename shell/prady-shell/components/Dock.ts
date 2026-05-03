import { Widget } from 'ags';

const apps = [
    { icon: 'utilities-terminal-symbolic', action: 'gnome-terminal' },
    { icon: 'web-browser-symbolic', action: 'firefox' },
    { icon: 'system-file-manager-symbolic', action: 'nautilus' }
];

const AppIcon = (app: any) => Widget.Button({
    className: 'dock-icon',
    onClicked: () => console.log(`Launch ${app.action}`),
    child: Widget.Icon({ icon: app.icon, size: 48 }),
});

const AskAiButton = () => Widget.Button({
    className: 'dock-icon ask-ai',
    onClicked: () => console.log("Open AI Spotlight Mode"),
    child: Widget.Icon({ icon: 'system-search-symbolic', size: 48 }),
});

export const Dock = () => Widget.Window({
    name: 'dock',
    anchor: ['bottom'],
    margins: [0, 0, 10, 0],
    child: Widget.Box({
        className: 'dock-container',
        spacing: 10,
        children: [
            ...apps.map(AppIcon),
            Widget.Separator({ vertical: true, className: 'dock-separator' }),
            AskAiButton()
        ]
    })
});

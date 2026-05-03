import { Widget, Variable } from 'ags';
import { VyrexStatus } from './VyrexStatus.js';

const time = Variable('', {
    poll: [1000, 'date "+%H:%M"'],
});

const Logo = () => Widget.Button({
    className: 'menu-logo',
    onClicked: () => console.log("Open System Menu"),
    child: Widget.Icon({ icon: 'start-here-symbolic' }),
});

const Clock = () => Widget.Label({
    className: 'menu-clock',
    label: time.bind(),
});

const SystemTray = () => Widget.Box({
    className: 'menu-tray',
    spacing: 8,
    children: [
        VyrexStatus(),
        Widget.Icon({ icon: 'network-wireless-signal-good-symbolic' }),
        Widget.Icon({ icon: 'audio-volume-high-symbolic' }),
        Widget.Icon({ icon: 'battery-level-80-symbolic' }),
        Widget.Button({
            className: 'ai-mic-btn',
            onClicked: () => console.log("Start Voice Task"),
            child: Widget.Icon({ icon: 'audio-input-microphone-symbolic' })
        })
    ]
});

export const MenuBar = () => Widget.Window({
    name: 'menubar',
    anchor: ['top', 'left', 'right'],
    exclusivity: 'exclusive',
    child: Widget.CenterBox({
        className: 'menubar-container',
        startWidget: Logo(),
        centerWidget: Clock(),
        endWidget: SystemTray(),
    }),
});

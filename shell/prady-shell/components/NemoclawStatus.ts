import { Widget, Variable } from 'ags';

// In a real implementation, this would poll the Vyrex socket
const modelName = Variable('Qwen2.5-7B');
const statusColor = Variable('green'); // green, orange, red

export const VyrexStatus = () => Widget.Box({
    className: 'vyrex-status',
    spacing: 4,
    children: [
        Widget.Label({
            className: 'vyrex-model',
            label: modelName.bind()
        }),
        Widget.Icon({
            className: 'vyrex-indicator',
            icon: 'media-record-symbolic',
            css: statusColor.bind().as(c => `color: ${c};`)
        })
    ]
});

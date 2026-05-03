import { App } from 'ags';
import { MenuBar } from './components/MenuBar.js';
import { Dock } from './components/Dock.js';
import { Spotlight } from './components/Spotlight.js';
import { PradyAssistant } from './components/PradyAssistant.js';

App.config({
    style: './style/global.css',
    windows: [
        MenuBar(),
        Dock(),
        Spotlight(),
        PradyAssistant()
    ],
});

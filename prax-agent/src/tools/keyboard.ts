import { ToolRegistry } from './registry.js';
import { exec } from 'child_process';
import { promisify } from 'util';

const execAsync = promisify(exec);

export function registerKeyboardTools(registry: ToolRegistry) {
  registry.register({
    name: 'keyboard_type',
    description: 'Types a string of text.',
    parameters: {
      type: 'object',
      properties: {
        text: { type: 'string' }
      },
      required: ['text']
    },
    execute: async (args: any) => {
      const { text } = args;
      try {
        await execAsync(`ydotool type -- "${text}"`);
        return { success: true, length: text.length };
      } catch (e: any) {
        console.warn(`[MOCK] ydotool type -- "${text}"`);
        return { success: false, error: e.message };
      }
    }
  });

  registry.register({
    name: 'keyboard_shortcut',
    description: 'Sends a combination of keys together, e.g., ["ctrl", "c"].',
    parameters: {
      type: 'object',
      properties: {
        keys: { type: 'array', items: { type: 'string' } }
      },
      required: ['keys']
    },
    execute: async (args: any) => {
      const { keys } = args;
      try {
        await execAsync(`ydotool key -- ${keys.join('+')}`);
        return { success: true, keys };
      } catch (e: any) {
        console.warn(`[MOCK] ydotool key -- ${keys.join('+')}`);
        return { success: false, error: e.message };
      }
    }
  });

  registry.register({
    name: 'keyboard_press',
    description: 'Presses a single key.',
    parameters: {
      type: 'object',
      properties: {
        key: { type: 'string' }
      },
      required: ['key']
    },
    execute: async (args: any) => {
      const { key } = args;
      try {
        await execAsync(`ydotool key -- ${key}`);
        return { success: true, key };
      } catch (e: any) {
        console.warn(`[MOCK] ydotool key -- ${key}`);
        return { success: false, error: e.message };
      }
    }
  });
}

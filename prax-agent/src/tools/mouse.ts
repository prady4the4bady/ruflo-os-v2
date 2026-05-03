import { ToolRegistry } from './registry.js';
import { exec } from 'child_process';
import { promisify } from 'util';

const execAsync = promisify(exec);

export function registerMouseTools(registry: ToolRegistry) {
  registry.register({
    name: 'mouse_move',
    description: 'Moves the mouse cursor to absolute coordinates.',
    parameters: {
      type: 'object',
      properties: {
        x: { type: 'number' },
        y: { type: 'number' },
        smooth: { type: 'boolean', default: true }
      },
      required: ['x', 'y']
    },
    execute: async (args: any) => {
      const { x, y } = args;
      try {
        await execAsync(`ydotool mousemove --absolute -x ${x} -y ${y}`);
        return { success: true, x, y };
      } catch (e: any) {
        console.warn(`[MOCK] ydotool mousemove -x ${x} -y ${y}`);
        return { success: false, error: e.message };
      }
    }
  });

  registry.register({
    name: 'mouse_click',
    description: 'Moves the mouse to coordinates and clicks.',
    parameters: {
      type: 'object',
      properties: {
        x: { type: 'number' },
        y: { type: 'number' },
        button: { type: 'string', enum: ['left', 'right', 'middle'], default: 'left' },
        double: { type: 'boolean', default: false }
      },
      required: ['x', 'y']
    },
    execute: async (args: any) => {
      const { x, y, button = 'left' } = args;
      const btnCode = button === 'right' ? 'C1' : button === 'middle' ? 'C2' : 'C0';
      try {
        await execAsync(`ydotool mousemove --absolute -x ${x} -y ${y} && ydotool click 0x${btnCode}`);
        return { success: true, x, y, button };
      } catch (e: any) {
        console.warn(`[MOCK] ydotool mousemove -x ${x} -y ${y} && ydotool click 0x${btnCode}`);
        return { success: false, error: e.message };
      }
    }
  });

  registry.register({
    name: 'mouse_scroll',
    description: 'Scrolls the mouse wheel up or down at a specific position.',
    parameters: {
      type: 'object',
      properties: {
        x: { type: 'number' },
        y: { type: 'number' },
        direction: { type: 'string', enum: ['up', 'down'] },
        amount: { type: 'number', default: 1 }
      },
      required: ['x', 'y', 'direction']
    },
    execute: async (args: any) => {
      const { x, y, direction, amount = 1 } = args;
      const dy = direction === 'up' ? -amount : amount;
      try {
        await execAsync(`ydotool mousemove --absolute -x ${x} -y ${y} && ydotool scroll -- ${dy}`);
        return { success: true };
      } catch (e: any) {
        console.warn(`[MOCK] ydotool scroll -- ${dy}`);
        return { success: false, error: e.message };
      }
    }
  });
}

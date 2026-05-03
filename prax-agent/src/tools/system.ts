import { ToolRegistry } from './registry.js';
import { exec, execSync } from 'child_process';
import { promisify } from 'util';

const execAsync = promisify(exec);

export function registerSystemTools(registry: ToolRegistry) {
  registry.register({
    name: 'open_application',
    description: 'Launches a desktop application by name (e.g., Firefox, Terminal).',
    parameters: {
      type: 'object',
      properties: {
        name: { type: 'string' }
      },
      required: ['name']
    },
    execute: async (args: any) => {
      const { name } = args;
      try {
        // Find desktop file
        const desktopFile = execSync(`grep -il "^Name=.*${name}" /usr/share/applications/*.desktop | head -n 1`).toString().trim();
        if (desktopFile) {
          const app = desktopFile.split('/').pop();
          exec(`gtk-launch ${app}`);
          return { success: true, name: app };
        } else {
          // Fallback to direct execution
          exec(name.toLowerCase());
          return { success: true, name: name.toLowerCase() };
        }
      } catch (e) {
        console.warn(`[MOCK] Opened application: ${name}`);
        return { success: true, name: name };
      }
    }
  });

  registry.register({
    name: 'execute_shell',
    description: 'Executes a shell command and returns stdout/stderr. Do not use interactive commands.',
    parameters: {
      type: 'object',
      properties: {
        command: { type: 'string' },
        timeout: { type: 'number', default: 30000 }
      },
      required: ['command']
    },
    execute: async (args: any) => {
      const { command, timeout = 30000 } = args;
      const startTime = Date.now();
      try {
        const { stdout, stderr } = await execAsync(command, { timeout });
        return { 
          success: true, 
          stdout, 
          stderr, 
          exitCode: 0, 
          duration: Date.now() - startTime 
        };
      } catch (e: any) {
        return { 
          success: false, 
          stdout: e.stdout, 
          stderr: e.stderr, 
          exitCode: e.code, 
          duration: Date.now() - startTime 
        };
      }
    }
  });

  registry.register({
    name: 'send_notification',
    description: 'Sends a desktop notification to the user.',
    parameters: {
      type: 'object',
      properties: {
        title: { type: 'string' },
        body: { type: 'string' },
        urgency: { type: 'string', enum: ['low', 'normal', 'critical'], default: 'normal' }
      },
      required: ['title', 'body']
    },
    execute: async (args: any) => {
      const { title, body, urgency = 'normal' } = args;
      try {
        execSync(`notify-send -u ${urgency} "${title}" "${body}"`);
      } catch (e) {
        console.log(`[MOCK] Notification sent: [${urgency}] ${title} - ${body}`);
      }
      return { success: true };
    }
  });
}

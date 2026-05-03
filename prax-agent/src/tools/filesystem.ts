import { ToolRegistry } from './registry.js';
import * as fs from 'fs/promises';
import * as path from 'path';

export function registerFilesystemTools(registry: ToolRegistry) {
  registry.register({
    name: 'read_file',
    description: 'Reads the contents of a file.',
    parameters: {
      type: 'object',
      properties: {
        path: { type: 'string', description: 'Absolute path to the file' }
      },
      required: ['path']
    },
    execute: async (args: any) => {
      try {
        const content = await fs.readFile(args.path, 'utf-8');
        return { success: true, content };
      } catch (e: any) {
        return { success: false, error: e.message };
      }
    }
  });

  registry.register({
    name: 'write_file',
    description: 'Writes data to a file. Overwrites existing files.',
    parameters: {
      type: 'object',
      properties: {
        path: { type: 'string', description: 'Absolute path to the file' },
        data: { type: 'string', description: 'Content to write' }
      },
      required: ['path', 'data']
    },
    execute: async (args: any) => {
      try {
        await fs.mkdir(path.dirname(args.path), { recursive: true });
        await fs.writeFile(args.path, args.data, 'utf-8');
        return { success: true };
      } catch (e: any) {
        return { success: false, error: e.message };
      }
    }
  });
}

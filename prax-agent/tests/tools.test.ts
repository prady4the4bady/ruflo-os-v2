import { expect, test, describe } from 'vitest';
import { ToolRegistry } from '../src/tools/registry.js';
import { registerFilesystemTools } from '../src/tools/filesystem.js';

describe('Tool Registry', () => {
  test('registers and lists tools', () => {
    const registry = new ToolRegistry();
    registerFilesystemTools(registry);
    
    const tools = registry.list();
    expect(tools.length).toBeGreaterThan(0);
    expect(registry.get('read_file')).toBeDefined();
  });

  test('validates arguments', async () => {
    const registry = new ToolRegistry();
    registerFilesystemTools(registry);
    
    // Should fail missing args
    await expect(registry.execute('read_file', {})).rejects.toThrow();
  });
});

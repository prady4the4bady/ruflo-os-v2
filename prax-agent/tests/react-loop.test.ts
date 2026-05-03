import { expect, test, describe } from 'vitest';
import { ReactLoop } from '../src/core/react-loop.js';
import { ToolRegistry } from '../src/tools/registry.js';
import { VyrexClient } from '../src/vyrex-client.js';
import { SessionMemory } from '../src/memory/session.js';

describe('ReAct Loop', () => {
  test('executes a basic plan mock', async () => {
    const registry = new ToolRegistry();
    // Register a dummy tool
    registry.register({
      name: 'execute_shell',
      description: 'mock',
      parameters: { type: 'object', properties: {} },
      execute: async () => ({ success: true })
    });

    const vyrex = new VyrexClient();
    const memory = new SessionMemory(':memory:'); // Use in-memory SQLite

    const loop = new ReactLoop(registry, vyrex, memory);
    
    const result = await loop.run("mock goal", "session_1");
    
    expect(result.success).toBe(true);
    expect(result.steps.length).toBe(1);
    expect(result.steps[0].action.toolName).toBe('execute_shell');
  });
});

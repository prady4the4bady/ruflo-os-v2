import { Tool } from '../types.js';

export class ToolRegistry {
  private tools: Map<string, Tool> = new Map();

  register(tool: Tool): void {
    if (this.tools.has(tool.name)) {
      throw new Error(`Tool ${tool.name} is already registered.`);
    }
    this.tools.set(tool.name, tool);
  }

  get(name: string): Tool | undefined {
    return this.tools.get(name);
  }

  list(): Tool[] {
    return Array.from(this.tools.values());
  }

  async execute(name: string, args: Record<string, unknown>): Promise<unknown> {
    const tool = this.tools.get(name);
    if (!tool) {
      throw new Error(`Tool ${name} not found.`);
    }
    if (!this.validateArgs(tool, args)) {
      throw new Error(`Invalid arguments for tool ${name}. Expected schema: ${JSON.stringify(tool.parameters)}`);
    }
    return tool.execute(args);
  }

  toOpenAIFunctions(): any[] {
    return this.list().map(tool => ({
      name: tool.name,
      description: tool.description,
      parameters: tool.parameters
    }));
  }

  validateArgs(tool: Tool, args: Record<string, unknown>): boolean {
    // Basic validation stub. In production, use AJV or similar JSON Schema validator.
    if (!tool.parameters || !tool.parameters.properties) return true;
    for (const key of Object.keys(tool.parameters.properties)) {
      if (tool.parameters.required?.includes(key) && args[key] === undefined) {
        return false;
      }
    }
    return true;
  }
}

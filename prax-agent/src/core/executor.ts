import { ToolRegistry } from '../tools/registry.js';
import { PlannedStep, ToolCall } from '../types.js';

export class Executor {
  constructor(private registry: ToolRegistry) {}

  async executeStep(step: PlannedStep): Promise<ToolCall> {
    console.log(`[Executor] Running: ${step.tool}`);
    let result: any;
    let error: string | undefined;

    try {
      result = await this.registry.execute(step.tool, step.args);
    } catch (e: any) {
      error = e.message;
      result = { success: false, error };
    }

    return {
      toolName: step.tool,
      args: step.args,
      result,
      error
    };
  }
}

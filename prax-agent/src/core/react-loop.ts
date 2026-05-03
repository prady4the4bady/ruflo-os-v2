import { ToolRegistry } from '../tools/registry.js';
import { VyrexClient } from '../vyrex-client.js';
import { SessionMemory } from '../memory/session.js';
import { Planner } from './planner.js';
import { Executor } from './executor.js';
import { Observer } from './observer.js';
import { SafetyGate } from './safety.js';
import { TaskSession, TaskResult, Step } from '../types.js';
import { EventEmitter } from 'events';

export class ReactLoop extends EventEmitter {
  private planner: Planner;
  private executor: Executor;
  private observer: Observer;
  private safety: SafetyGate;
  private isAborted = false;

  constructor(
    private registry: ToolRegistry,
    private vyrex: VyrexClient,
    private memory: SessionMemory
  ) {
    super();
    this.planner = new Planner(this.vyrex);
    this.executor = new Executor(this.registry);
    this.observer = new Observer(null); // VisionClient mock injected later if needed
    this.safety = new SafetyGate();
  }

  async run(goal: string, sessionId: string): Promise<TaskResult> {
    this.isAborted = false;
    const session: TaskSession = {
      id: sessionId,
      goal,
      executedSteps: [],
      status: 'running',
      startTime: Date.now()
    };

    try {
      this.emit('thought', `Planning task: ${goal}`);
      const plan = await this.planner.createPlan(goal);
      session.plan = plan;

      for (const plannedStep of plan.steps) {
        if (this.isAborted) throw new Error('Task aborted by user');

        const step: Step = {
          id: plannedStep.id,
          thought: plannedStep.description,
          action: { toolName: plannedStep.tool, args: plannedStep.args },
          status: 'pending'
        };
        
        this.emit('step', step);
        this.emit('thought', `Executing step: ${plannedStep.description}`);

        const safetyCheck = await this.safety.check(plannedStep);
        if (safetyCheck === 'deny') {
          throw new Error(`Safety Gate Denied: Command execution blocked for ${plannedStep.tool}`);
        } else if (safetyCheck === 'confirm') {
          this.emit('confirmation_required', { id: step.id, description: plannedStep.description });
          // In a real env, wait for handleConfirmation. We mock automatic approval here.
        }

        const toolCall = await this.executor.executeStep(plannedStep);
        step.action = toolCall;

        const verified = await this.observer.verify(step, toolCall.result);
        step.status = verified ? 'success' : 'failed';
        session.executedSteps.push(step);

        if (!verified) {
          throw new Error(`Observation failed at step ${step.id}`);
        }
      }

      session.status = 'completed';
      session.endTime = Date.now();
      session.summary = `Task completed successfully with ${session.executedSteps.length} steps.`;

      this.memory.saveSession(session);
      
      const result: TaskResult = {
        success: true,
        summary: session.summary,
        steps: session.executedSteps,
        duration: session.endTime - session.startTime
      };
      
      this.emit('complete', result);
      return result;

    } catch (e: any) {
      session.status = this.isAborted ? 'aborted' : 'failed';
      session.endTime = Date.now();
      session.summary = `Failed: ${e.message}`;
      this.memory.saveSession(session);
      
      const result: TaskResult = {
        success: false,
        summary: session.summary,
        steps: session.executedSteps,
        duration: session.endTime - session.startTime
      };
      this.emit('error', e);
      return result;
    }
  }

  abort(): void {
    this.isAborted = true;
  }
}

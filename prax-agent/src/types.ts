export interface Tool {
  name: string;
  description: string;
  parameters: any; // JSON Schema Object
  execute: (args: any) => Promise<any>;
}

export interface ToolCall {
  toolName: string;
  args: Record<string, unknown>;
  result?: unknown;
  error?: string;
}

export interface Step {
  id: string;
  thought: string;
  action: ToolCall;
  observation?: unknown;
  status: 'pending' | 'success' | 'failed';
}

export interface PlannedStep {
  id: string;
  description: string;
  tool: string;
  args: Record<string, unknown>;
  expectedOutcome: string;
  isSensitive: boolean;
}

export interface TaskPlan {
  goal: string;
  steps: PlannedStep[];
  context?: string;
}

export interface TaskSession {
  id: string;
  goal: string;
  plan?: TaskPlan;
  executedSteps: Step[];
  status: 'running' | 'completed' | 'failed' | 'aborted';
  startTime: number;
  endTime?: number;
  summary?: string;
}

export interface VyrexMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
}

export interface VyrexRequest {
  model: string;
  messages: VyrexMessage[];
  stream?: boolean;
  temperature?: number;
  max_tokens?: number;
}

export interface ScreenState {
  screenshot: Buffer;
  ocrText: string;
  timestamp: number;
}

export interface Coordinate {
  x: number;
  y: number;
}

export type MouseButton = 'left' | 'right' | 'middle';

export interface TextBlock {
  text: string;
  bbox: { x: number; y: number; w: number; h: number };
  confidence: number;
}

export interface TaskResult {
  success: boolean;
  summary: string;
  steps: Step[];
  duration: number;
}

export interface Macro {
  id: string;
  goal_pattern: string;
  steps_json: string;
  success_count: number;
  created_at: number;
  last_used_at: number;
}

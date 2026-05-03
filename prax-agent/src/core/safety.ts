import { PlannedStep } from '../types.js';

export class SafetyGate {
  private static BLOCKED_COMMANDS = [
    /rm\s+-rf\s+\//,
    /mkfs/,
    /dd\s+if=.*of=\/dev/,
    /chmod\s+777\s+\//,
    /chown\s+-R\s+root/
  ];

  async check(step: PlannedStep): Promise<'allow' | 'confirm' | 'deny'> {
    // Check blocklist for shell commands
    if (step.tool === 'execute_shell' && step.args.command) {
      const cmd = String(step.args.command);
      for (const pattern of SafetyGate.BLOCKED_COMMANDS) {
        if (pattern.test(cmd)) {
          return 'deny';
        }
      }
    }

    if (step.isSensitive) {
      return 'confirm';
    }

    return 'allow';
  }

  handleConfirmation(requestId: string, allowed: boolean): void {
    // In a real GUI, this resumes the blocked step event loop
    console.log(`Confirmation ${requestId}: ${allowed ? 'Allowed' : 'Denied'}`);
  }
}

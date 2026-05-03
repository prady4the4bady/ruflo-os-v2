import { Lumyn } from './lumyn.js';

/**
 * Adapter connecting our local Lumyn wrapper to the upstream Lumyn-Agent repo logic.
 * The upstream Lumyn-Agent typically expects raw LLM generation strings that it parses.
 */
export class LumynUpstreamAdapter {
  constructor(private localLumyn: Lumyn) {}

  async evaluateUpstreamPrompt(prompt: string, context: string): Promise<string> {
    const response = await this.localLumyn.reason(prompt, context);
    // Format the response back into what upstream lumyn parsers might expect
    return `<thinking>\n${response.thinking}\n</thinking>\n${response.answer}`;
  }
}

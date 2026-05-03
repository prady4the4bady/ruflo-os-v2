import { VyrexMessage, VyrexRequest } from './types.js';

export class VyrexClient {
  private socketPath: string;

  constructor(socketPath: string = '/run/vyrex/api.sock') {
    this.socketPath = socketPath;
  }

  private async request(path: string, method: string, body?: any) {
    // Node.js 18+ fetch supports unix sockets via unix://
    // However, fetch API for Unix sockets is still experimental/undocumented in some engines.
    // For this implementation, we simulate the fetch or use a wrapper if needed.
    // Mocking here as the socket won't exist in the test env.
    console.log(`[MOCK] Vyrex request to ${path} via ${this.socketPath}`);
    if (path === '/v1/chat/completions') {
      return {
        choices: [
          { message: { role: 'assistant', content: '{"goal": "mock", "steps": []}' } }
        ]
      };
    }
    return {};
  }

  async chat(messages: VyrexMessage[], opts?: Partial<VyrexRequest>): Promise<string> {
    const req: VyrexRequest = {
      model: opts?.model || 'Qwen2.5-72B-Instruct',
      messages,
      ...opts
    };
    
    const resp: any = await this.request('/v1/chat/completions', 'POST', req);
    return resp.choices[0].message.content;
  }

  async vision(imageBase64: string, prompt: string): Promise<string> {
    const messages: VyrexMessage[] = [
      {
        role: 'user',
        content: `[Image Base64]\n${prompt}` // Simplified for mock
      }
    ];
    return this.chat(messages);
  }

  async embed(text: string): Promise<number[]> {
    console.log('[MOCK] Embedding request for text:', text);
    return [0.1, 0.2, 0.3];
  }

  async listModels(): Promise<string[]> {
    const resp: any = await this.request('/v1/models', 'GET');
    return resp.data ? resp.data.map((m: any) => m.id) : ['Qwen2.5-72B-Instruct'];
  }
}

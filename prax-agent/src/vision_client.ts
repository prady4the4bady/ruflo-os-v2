export class VisionClient {
  private url: string;

  constructor(url: string = 'http://127.0.0.1:7890') {
    this.url = url;
  }

  async ocr(imageBase64: string): Promise<{ text: string, blocks: any[] }> {
    try {
      const resp = await fetch(`${this.url}/ocr`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ image_base64: imageBase64 })
      });
      return await resp.json();
    } catch (e) {
      console.warn('[MOCK] Vision service unreachable. Returning mock OCR.');
      return { text: "Mock Screen Text", blocks: [] };
    }
  }

  async findElement(imageBase64: string, description: string): Promise<{ found: boolean, x: number, y: number, confidence: number }> {
    try {
      const resp = await fetch(`${this.url}/find`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ image_base64: imageBase64, description })
      });
      return await resp.json();
    } catch (e) {
      console.warn(`[MOCK] Vision service unreachable. Mock findElement for '${description}'`);
      return { found: true, x: 100, y: 100, confidence: 0.95 };
    }
  }
}

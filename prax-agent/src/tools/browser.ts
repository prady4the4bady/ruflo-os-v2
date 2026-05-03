import { ToolRegistry } from './registry.js';
import { chromium, Browser } from 'playwright';

let browserInstance: Browser | null = null;

async function getBrowser() {
  if (!browserInstance) {
    browserInstance = await chromium.launch({ headless: true });
  }
  return browserInstance;
}

export function registerBrowserTools(registry: ToolRegistry) {
  registry.register({
    name: 'browse_web',
    description: 'Opens a URL in a headless browser and returns readable text and page title.',
    parameters: {
      type: 'object',
      properties: {
        url: { type: 'string' }
      },
      required: ['url']
    },
    execute: async (args: any) => {
      const browser = await getBrowser();
      const page = await browser.newPage();
      try {
        await page.goto(args.url, { waitUntil: 'networkidle' });
        const title = await page.title();
        const text = await page.evaluate(() => document.body.innerText);
        const screenshot = await page.screenshot({ type: 'jpeg', quality: 50 });
        
        return {
          success: true,
          title,
          url: page.url(),
          text: text.substring(0, 10000), // Limit text to 10k chars
          screenshot: screenshot.toString('base64')
        };
      } catch (e: any) {
        return { success: false, error: e.message };
      } finally {
        await page.close();
      }
    }
  });

  registry.register({
    name: 'search_web',
    description: 'Performs a web search using DuckDuckGo.',
    parameters: {
      type: 'object',
      properties: {
        query: { type: 'string' }
      },
      required: ['query']
    },
    execute: async (args: any) => {
      const browser = await getBrowser();
      const page = await browser.newPage();
      try {
        const searchUrl = `https://html.duckduckgo.com/html/?q=${encodeURIComponent(args.query)}`;
        await page.goto(searchUrl, { waitUntil: 'networkidle' });
        
        const results = await page.evaluate(() => {
          const links = Array.from(document.querySelectorAll('.result__snippet'));
          return links.slice(0, 5).map((el: any) => ({
            snippet: el.innerText,
            url: el.closest('.result').querySelector('.result__url').getAttribute('href')
          }));
        });
        
        return { success: true, results };
      } catch (e: any) {
        return { success: false, error: e.message };
      } finally {
        await page.close();
      }
    }
  });
}

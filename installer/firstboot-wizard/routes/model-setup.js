const { spawn } = require('child_process');

module.exports = (req, res) => {
  const modelId = req.body.modelId;
  const apiKey = req.body.apiKey || '';
  
  if (!modelId) {
    return res.status(400).json({ error: 'No modelId provided' });
  }

  res.setHeader('Content-Type', 'text/event-stream');
  res.setHeader('Cache-Control', 'no-cache');
  res.setHeader('Connection', 'keep-alive');

  let downloadProcess;

  if (modelId.startsWith('nvidia/')) {
    // Cloud model via Vyrex
    downloadProcess = spawn('/usr/local/bin/vyrex', ['onboard', '--api-key', apiKey, '--non-interactive']);
  } else if (modelId.includes('github.com')) {
    // GitHub repo
    const name = modelId.split('/').pop().replace('.git', '');
    downloadProcess = spawn('git', ['clone', '--depth=1', modelId, `/opt/models/github/${name}`]);
  } else if (modelId.includes('/')) {
    // HuggingFace ID
    const name = modelId.split('/').pop();
    downloadProcess = spawn('huggingface-cli', ['download', modelId, '--local-dir', `/opt/models/huggingface/${name}`]);
  } else {
    // Local via Ollama
    downloadProcess = spawn('ollama', ['pull', modelId]);
  }

  downloadProcess.stdout.on('data', (data) => {
    const lines = data.toString().split('\n');
    for (const line of lines) {
      if (line.trim()) {
        res.write(`data: ${JSON.stringify({ message: line })}\n\n`);
      }
    }
  });

  downloadProcess.stderr.on('data', (data) => {
    const lines = data.toString().split('\n');
    for (const line of lines) {
      if (line.trim()) {
        res.write(`data: ${JSON.stringify({ error: line })}\n\n`);
      }
    }
  });

  downloadProcess.on('close', (code) => {
    res.write(`data: ${JSON.stringify({ done: true, code })}\n\n`);
    res.end();
  });
};

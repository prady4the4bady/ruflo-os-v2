const express = require('express');
const path = require('path');
const fs = require('fs');
const hardwareDetect = require('./routes/hardware-detect');
const modelSetup = require('./routes/model-setup');

const app = express();
const port = 3000;

app.use(express.static(path.join(__dirname, 'public')));
app.use(express.json());

app.post('/api/save-keys', (req, res) => {
  const { nvidia_key, anthropic_key } = req.body;
  const content = `ANTHROPIC_API_KEY=${anthropic_key || ''}\nNVIDIA_API_KEY=${nvidia_key || ''}\n`;
  try {
    if (!fs.existsSync('/etc/kryos')) {
      fs.mkdirSync('/etc/kryos', { recursive: true });
    }
    fs.writeFileSync('/etc/kryos/api-keys.env', content);
    res.json({ success: true });
  } catch (err) {
    console.error("Failed to save keys:", err);
    res.status(500).json({ error: "Failed to save keys" });
  }
});

app.get('/api/hardware-detect', hardwareDetect);
app.post('/api/model-setup', modelSetup);

app.listen(port, () => {
  console.log(`PradyOS First Boot Wizard running at http://localhost:${port}`);
});

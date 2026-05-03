const { execSync } = require('child_process')

module.exports = (req, res) => {
  let gpu = "None"
  let vram = "0"
  let ram = "0"
  let cores = "1"
  
  try {
    gpu = execSync('lspci | grep -i vga 2>/dev/null || echo "None"').toString().trim()
    vram = execSync("nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits 2>/dev/null || echo 0").toString().trim()
    ram = execSync("free -g 2>/dev/null | awk '/^Mem/{print $2}' || echo 0").toString().trim()
    cores = execSync("nproc 2>/dev/null || echo 1").toString().trim()
  } catch (e) {
    // Ignore errors
  }
  
  let recommended = 'cloud-only mode via Vyrex + NVIDIA API key'
  let modelHF = 'nvidia/nemotron-3-super-120b-a12b'
  
  const vramInt = parseInt(vram) || 0;
  
  if (vramInt >= 24000) {
    recommended = 'nvidia/nemotron-3-super-120b-a12b (cloud via Vyrex)'
    modelHF = 'nvidia/nemotron-3-super-120b-a12b'
  } else if (vramInt >= 12000) {
    recommended = 'mistral-7b-instruct-v0.3 (local via Ollama)'
    modelHF = 'mistral-7b-instruct-v0.3'
  } else if (vramInt >= 6000) {
    recommended = 'phi-3-mini-128k-instruct (local via Ollama)'
    modelHF = 'phi-3-mini-128k-instruct'
  }
  
  res.json({ gpu, vram, ram, cores, recommended, modelHF })
}

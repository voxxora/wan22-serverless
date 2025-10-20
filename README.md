# Wan 2.2 Official Serverless for RunPod

Deploy official Wan 2.2 models as serverless endpoints (pay per request).

## 🚀 Quick Deploy

### 1. Push to GitHub

```bash
cd wan22-serverless
git init
git add .
git commit -m "Wan 2.2 serverless handler"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/wan22-serverless.git
git push -u origin main
```

### 2. Create RunPod Serverless Endpoint

1. Go to https://www.runpod.io/console/serverless
2. Click "New Endpoint"
3. **Template Settings:**
   - Name: `Wan 2.2 Official`
   - Container Image: Build from GitHub
   - GitHub Repo: `YOUR_USERNAME/wan22-serverless`
   - Docker Command: `python3 -u /workspace/handler.py`

4. **GPU Settings:**
   - Min Workers: 0
   - Max Workers: 3
   - GPU Type: A100 80GB (for all models) OR RTX 4090 (for TI2V only)
   - Container Disk: 50GB

5. **Network Volume:**
   - Create network volume (100GB+)
   - Mount at: `/runpod-volume`

6. Click "Deploy"

### 3. Upload Models to Network Volume

You need to upload Wan 2.2 models to your network volume.

**Option A: Via RunPod SSH**
```bash
# SSH into network volume pod
ssh root@your-pod-ip

# Download models
pip install huggingface_hub

# TI2V-5B (smallest)
huggingface-cli download Wan-AI/Wan2.2-TI2V-5B --local-dir /runpod-volume/Wan2.2-TI2V-5B

# T2V-A14B (if you have 80GB GPU)
huggingface-cli download Wan-AI/Wan2.2-T2V-A14B --local-dir /runpod-volume/Wan2.2-T2V-A14B

# I2V-A14B (if you have 80GB GPU)
huggingface-cli download Wan-AI/Wan2.2-I2V-A14B --local-dir /runpod-volume/Wan2.2-I2V-A14B
```

**Option B: Via RunPod File Manager**
1. Go to RunPod console
2. Open network volume
3. Upload model files

### 4. Test Endpoint

```bash
# Get your endpoint ID from RunPod dashboard
export ENDPOINT_ID=your-endpoint-id
export RUNPOD_API_KEY=your-api-key

# Test T2V
curl -X POST https://api.runpod.ai/v2/${ENDPOINT_ID}/run \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${RUNPOD_API_KEY}" \
  -d '{
    "input": {
      "task": "t2v",
      "prompt": "A cat walking on the beach at sunset",
      "width": 1280,
      "height": 720
    }
  }'

# Get result
curl https://api.runpod.ai/v2/${ENDPOINT_ID}/status/JOB_ID \
  -H "Authorization: Bearer ${RUNPOD_API_KEY}"
```

### 5. Update Frontend

In your `.env`:
```bash
VITE_WAN22_T2V_ENDPOINT=your-t2v-endpoint-id
VITE_WAN22_I2V_ENDPOINT=your-i2v-endpoint-id
VITE_WAN22_TI2V_ENDPOINT=your-ti2v-endpoint-id
VITE_RUNPOD_API_KEY=your-runpod-api-key
```

## 📋 API Reference

### Input Parameters

```json
{
  "input": {
    "task": "t2v|i2v|ti2v",
    "prompt": "Your prompt here",
    "image_base64": "base64_string (for i2v/ti2v)",
    "width": 1280,
    "height": 720,
    "num_frames": 121,
    "steps": 50,
    "guidance_scale": 7.5,
    "seed": 42
  }
}
```

### Output

```json
{
  "video": "data:video/mp4;base64,...",
  "info": {
    "task": "t2v",
    "resolution": "1280x720",
    "frames": 121,
    "fps": 24
  }
}
```

## 🎯 Model Selection

| Model | GPU Needed | Task | Best For |
|-------|-----------|------|----------|
| TI2V-5B | RTX 4090 (24GB) | T2V + I2V | Fast, affordable |
| T2V-A14B | A100 (80GB) | T2V only | Best quality T2V |
| I2V-A14B | A100 (80GB) | I2V only | Best quality I2V |

**Recommendation:** Start with TI2V-5B on RTX 4090 ($0.50/hour when active)

## 💰 Pricing

**RunPod Serverless:**
- Min workers: 0 (no cost when idle)
- Pay only when generating
- RTX 4090: ~$0.50/hour active time
- A100 80GB: ~$2/hour active time

**Example costs:**
- Generate 1 video (9 min): RTX 4090 = $0.08
- Generate 10 videos: RTX 4090 = $0.80
- Idle time: $0

## 🐛 Troubleshooting

**"Model not found"**
- Upload models to network volume at `/runpod-volume/Wan2.2-*`

**"Out of memory"**
- Use TI2V-5B model (24GB)
- Reduce `num_frames`
- Use smaller GPU

**"Build failed"**
- Check Dockerfile syntax
- Verify GitHub repo is public
- Check build logs in RunPod

**"Generation times out"**
- Increase timeout in RunPod settings
- Use faster model (TI2V-5B)
- Reduce frames/resolution

## ✅ Success Checklist

- [ ] GitHub repo created and pushed
- [ ] RunPod endpoint created
- [ ] Network volume created (100GB+)
- [ ] Models uploaded to network volume
- [ ] Endpoint test successful
- [ ] Frontend `.env` updated
- [ ] First video generated!

## 🎉 You're Done!

Your official Wan 2.2 serverless endpoint is ready!

**Pay only when generating. No hourly costs when idle.**

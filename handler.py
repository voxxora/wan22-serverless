"""
RunPod Serverless Handler for Wan 2.2 Official Models
100% Compatible with Official Wan 2.2 GitHub Implementation
Supports: TI2V-5B (T2V + I2V), T2V-A14B, I2V-A14B

Official Repo: https://github.com/Wan-Video/Wan2.2
"""

import runpod
import os
import sys
import base64
import subprocess
import tempfile
import json
from pathlib import Path

# Model paths
MODELS_DIR = Path("/workspace")  # Models stored here

# Model configurations from official docs
MODEL_CONFIGS = {
    "ti2v-5B": {
        "path": MODELS_DIR / "Wan2.2-TI2V-5B",
        "default_size": "1280*704",  # IMPORTANT: TI2V uses 704 height, not 720!
        "alt_size": "704*1280",
        "supports_t2v": True,
        "supports_i2v": True,
        "vram": "24GB",
        "command": "python /workspace/Wan2.2/generate.py"
    },
    "t2v-A14B": {
        "path": MODELS_DIR / "Wan2.2-T2V-A14B",
        "default_size": "1280*720",
        "alt_size": "854*480",
        "supports_t2v": True,
        "supports_i2v": False,
        "vram": "80GB",
        "command": "python /workspace/Wan2.2/generate.py"
    },
    "i2v-A14B": {
        "path": MODELS_DIR / "Wan2.2-I2V-A14B",
        "default_size": "1280*720",
        "alt_size": "854*480",
        "supports_t2v": False,
        "supports_i2v": True,
        "vram": "80GB",
        "command": "python /workspace/Wan2.2/generate.py"
    }
}

def check_wan_installation():
    """Verify Wan 2.2 is installed"""
    wan_path = Path("/workspace/Wan2.2")
    generate_script = wan_path / "generate.py"
    
    if not wan_path.exists():
        print("⚠️ Wan 2.2 not found at /workspace/Wan2.2")
        print("📥 Cloning Wan 2.2 repository...")
        subprocess.run([
            "git", "clone", 
            "https://github.com/Wan-Video/Wan2.2.git",
            str(wan_path)
        ], check=True)
        
        print("📦 Installing dependencies...")
        subprocess.run([
            "pip", "install", "-r", 
            str(wan_path / "requirements.txt")
        ], check=True)
    
    return generate_script.exists()

def download_model_if_needed(model_name):
    """Download model if not present"""
    config = MODEL_CONFIGS.get(model_name)
    if not config:
        raise ValueError(f"Unknown model: {model_name}")
    
    model_path = config["path"]
    
    if model_path.exists():
        print(f"✅ Model found: {model_path}")
        return True
    
    print(f"📥 Downloading {model_name}...")
    
    # Convert model name to HuggingFace format
    hf_name = f"Wan-AI/Wan2.2-{model_name.upper()}"
    
    subprocess.run([
        "huggingface-cli", "download",
        hf_name,
        "--local-dir", str(model_path)
    ], check=True)
    
    print(f"✅ Model downloaded: {model_path}")
    return True

def save_temp_image(image_base64):
    """Save base64 image to temp file"""
    if "base64," in image_base64:
        image_base64 = image_base64.split("base64,")[1]
    
    image_bytes = base64.b64decode(image_base64)
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg", mode='wb') as f:
        f.write(image_bytes)
        return f.name

def run_wan_generate(model_name, params):
    """
    Run official Wan 2.2 generate.py script
    This ensures 100% compatibility with official implementation
    """
    config = MODEL_CONFIGS[model_name]
    
    # Build command exactly as in official docs
    cmd = [
        "python3", "/workspace/Wan2.2/generate.py",
        "--task", model_name,
        "--size", params["size"],
        "--ckpt_dir", str(config["path"]),
        "--offload_model", "True",
        "--convert_model_dtype"
    ]
    
    # Add TI2V-specific flag
    if model_name == "ti2v-5B":
        cmd.extend(["--t5_cpu"])
    
    # Add prompt
    if params.get("prompt"):
        cmd.extend(["--prompt", params["prompt"]])
    
    # Add image if provided (for I2V or TI2V)
    if params.get("image_path"):
        cmd.extend(["--image", params["image_path"]])
    
    # Add seed if provided
    if params.get("seed"):
        cmd.extend(["--seed", str(params["seed"])])
    
    print(f"🎬 Running command: {' '.join(cmd)}")
    
    # Run generation
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd="/workspace/Wan2.2"
    )
    
    if result.returncode != 0:
        print(f"❌ Generation failed: {result.stderr}")
        raise Exception(f"Generation failed: {result.stderr}")
    
    print(f"✅ Generation completed")
    print(result.stdout)
    
    # Find output video (Wan saves to outputs/ directory)
    output_dir = Path("/workspace/Wan2.2/outputs")
    
    # Find most recent video file
    video_files = sorted(output_dir.glob("*.mp4"), key=lambda x: x.stat().st_mtime, reverse=True)
    
    if not video_files:
        raise Exception("No output video found")
    
    return video_files[0]

def generate_video(job):
    """
    Main handler - Routes to correct Wan 2.2 model
    """
    job_input = job["input"]
    
    try:
        # Check Wan installation
        if not check_wan_installation():
            raise Exception("Wan 2.2 installation failed")
        
        # Parse input
        model_name = job_input.get("model", "ti2v-5B")  # Default to TI2V-5B
        prompt = job_input.get("prompt", "")
        image_base64 = job_input.get("image_base64")
        
        # Validate model
        if model_name not in MODEL_CONFIGS:
            raise ValueError(f"Unknown model: {model_name}. Available: {list(MODEL_CONFIGS.keys())}")
        
        config = MODEL_CONFIGS[model_name]
        
        # Download model if needed
        download_model_if_needed(model_name)
        
        # Determine task mode
        has_image = bool(image_base64)
        is_t2v = not has_image
        is_i2v = has_image
        
        # Validate task compatibility
        if is_t2v and not config["supports_t2v"]:
            raise ValueError(f"{model_name} does not support text-to-video")
        
        if is_i2v and not config["supports_i2v"]:
            raise ValueError(f"{model_name} does not support image-to-video")
        
        # Prepare parameters
        params = {
            "size": job_input.get("size", config["default_size"]),
            "prompt": prompt if prompt else None,
            "seed": job_input.get("seed")
        }
        
        # Save image to temp file if provided
        if image_base64:
            params["image_path"] = save_temp_image(image_base64)
        
        print(f"🎯 Model: {model_name}")
        print(f"📝 Mode: {'Text-to-Video' if is_t2v else 'Image-to-Video'}")
        print(f"📏 Size: {params['size']}")
        print(f"💬 Prompt: {params.get('prompt', 'None')[:50]}...")
        
        # Run generation using official script
        output_video_path = run_wan_generate(model_name, params)
        
        # Convert video to base64
        with open(output_video_path, "rb") as f:
            video_bytes = f.read()
            video_base64 = base64.b64encode(video_bytes).decode('utf-8')
        
        # Cleanup
        if params.get("image_path"):
            os.unlink(params["image_path"])
        
        os.unlink(output_video_path)
        
        print("✅ Video generation successful")
        
        return {
            "status": "success",
            "video": f"data:video/mp4;base64,{video_base64}",
            "info": {
                "model": model_name,
                "mode": "t2v" if is_t2v else "i2v",
                "size": params["size"],
                "prompt": params.get("prompt", ""),
                "fps": 24
            }
        }
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        
        return {
            "status": "error",
            "error": str(e),
            "traceback": traceback.format_exc()
        }

# Start RunPod handler
runpod.serverless.start({"handler": generate_video})

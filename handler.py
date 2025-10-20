"""
RunPod Serverless Handler for Wan 2.2 Official Models
Supports T2V, I2V, TI2V generation
"""

import runpod
import torch
import os
import sys
import base64
import tempfile
from pathlib import Path

# Add Wan2.2 to path
sys.path.insert(0, '/workspace/Wan2.2')

# Import Wan modules
from wan.pipelines.pipeline_wan import WanPipeline
from wan.models.transformers import Wan2Model
from wan.utils.utils import save_video

# Global model cache
MODEL_CACHE = {}
MODELS_DIR = Path("/runpod-volume")  # RunPod network volume

def download_models_if_needed():
    """Download models to network volume if not present"""
    # Check which models are available
    models_to_check = {
        "t2v": MODELS_DIR / "Wan2.2-T2V-A14B",
        "i2v": MODELS_DIR / "Wan2.2-I2V-A14B",
        "ti2v": MODELS_DIR / "Wan2.2-TI2V-5B"
    }
    
    available = {}
    for task, path in models_to_check.items():
        if path.exists():
            print(f"✅ {task.upper()} model found at {path}")
            available[task] = str(path)
        else:
            print(f"⚠️ {task.upper()} model not found at {path}")
    
    return available

def load_model(task, model_path):
    """Load Wan model"""
    cache_key = f"{task}_{model_path}"
    
    if cache_key in MODEL_CACHE:
        print(f"📦 Using cached {task.upper()} model")
        return MODEL_CACHE[cache_key]
    
    print(f"🔄 Loading {task.upper()} model from {model_path}...")
    
    try:
        # Load model based on task
        if task == "ti2v":
            # TI2V-5B model
            model = WanPipeline.from_pretrained(
                model_path,
                torch_dtype=torch.float16,
                variant="fp16"
            )
        else:
            # T2V or I2V A14B models
            model = WanPipeline.from_pretrained(
                model_path,
                torch_dtype=torch.float16
            )
        
        model = model.to("cuda")
        MODEL_CACHE[cache_key] = model
        
        print(f"✅ {task.upper()} model loaded successfully")
        return model
        
    except Exception as e:
        print(f"❌ Failed to load {task.upper()} model: {e}")
        raise

def generate_video(job):
    """Main generation function"""
    job_input = job["input"]
    
    # Get task type
    task = job_input.get("task", "ti2v")  # t2v, i2v, ti2v
    prompt = job_input.get("prompt", "")
    
    # Image input (for i2v, ti2v)
    image_base64 = job_input.get("image_base64")
    image_url = job_input.get("image_url")
    
    # Parameters
    width = job_input.get("width", 1280)
    height = job_input.get("height", 720 if task != "ti2v" else 704)
    num_frames = job_input.get("num_frames", 121)  # ~5 seconds at 24fps
    num_inference_steps = job_input.get("steps", 50)
    guidance_scale = job_input.get("guidance_scale", 7.5)
    seed = job_input.get("seed", None)
    
    print(f"🎬 Starting {task.upper()} generation...")
    print(f"📝 Prompt: {prompt}")
    print(f"📏 Resolution: {width}x{height}, Frames: {num_frames}")
    
    try:
        # Get available models
        available_models = download_models_if_needed()
        
        if task not in available_models:
            raise ValueError(f"{task.upper()} model not available. Please upload model to /runpod-volume/Wan2.2-{task.upper()}-*")
        
        # Load model
        model_path = available_models[task]
        pipeline = load_model(task, model_path)
        
        # Prepare inputs
        generator = torch.Generator("cuda").manual_seed(seed) if seed else None
        
        # Handle image input
        image = None
        if task in ["i2v", "ti2v"] and (image_base64 or image_url):
            if image_base64:
                # Decode base64 image
                if "base64," in image_base64:
                    image_base64 = image_base64.split("base64,")[1]
                
                image_bytes = base64.b64decode(image_base64)
                
                # Save to temp file
                with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as f:
                    f.write(image_bytes)
                    image_path = f.name
                
                from PIL import Image as PILImage
                image = PILImage.open(image_path)
                
            elif image_url:
                # Download image from URL
                import requests
                from PIL import Image as PILImage
                from io import BytesIO
                
                response = requests.get(image_url)
                image = PILImage.open(BytesIO(response.content))
        
        # Generate video
        print("🎥 Generating video...")
        
        if task == "t2v":
            # Text-to-Video
            output = pipeline(
                prompt=prompt,
                height=height,
                width=width,
                num_frames=num_frames,
                num_inference_steps=num_inference_steps,
                guidance_scale=guidance_scale,
                generator=generator
            )
        
        elif task == "i2v":
            # Image-to-Video
            if image is None:
                raise ValueError("Image required for I2V task")
            
            output = pipeline(
                prompt=prompt,
                image=image,
                height=height,
                width=width,
                num_frames=num_frames,
                num_inference_steps=num_inference_steps,
                guidance_scale=guidance_scale,
                generator=generator
            )
        
        elif task == "ti2v":
            # Text+Image-to-Video (hybrid)
            output = pipeline(
                prompt=prompt,
                image=image,  # Can be None for text-only
                height=height,
                width=width,
                num_frames=num_frames,
                num_inference_steps=num_inference_steps,
                guidance_scale=guidance_scale,
                generator=generator
            )
        
        # Get video frames
        video_frames = output.frames[0]  # [num_frames, H, W, C]
        
        # Save video to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as f:
            output_path = f.name
        
        save_video(video_frames, output_path, fps=24)
        
        # Convert to base64
        with open(output_path, "rb") as f:
            video_bytes = f.read()
            video_base64 = base64.b64encode(video_bytes).decode('utf-8')
        
        # Cleanup
        os.unlink(output_path)
        if image and image_path:
            os.unlink(image_path)
        
        print("✅ Video generated successfully")
        
        return {
            "video": f"data:video/mp4;base64,{video_base64}",
            "info": {
                "task": task,
                "resolution": f"{width}x{height}",
                "frames": num_frames,
                "fps": 24
            }
        }
        
    except Exception as e:
        print(f"❌ Generation failed: {e}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}

# RunPod handler
runpod.serverless.start({"handler": generate_video})

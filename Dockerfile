FROM nvidia/cuda:12.1.0-cudnn8-devel-ubuntu22.04

# Install Python 3.10 and system dependencies
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3-pip \
    git \
    wget \
    ffmpeg \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /workspace

# Clone Wan2.2 official repo
RUN git clone https://github.com/Wan-Video/Wan2.2.git /workspace/Wan2.2
WORKDIR /workspace/Wan2.2

# Install PyTorch with CUDA 12.1
RUN pip3 install --no-cache-dir torch>=2.4.0 torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# Install packaging first (required by flash_attn)
RUN pip3 install --no-cache-dir packaging ninja

# Install ALL Wan requirements (base + s2v + animate)
# The codebase imports all modules on startup even if not used
RUN pip3 install --no-cache-dir -r requirements.txt && \
    pip3 install --no-cache-dir -r requirements_s2v.txt && \
    pip3 install --no-cache-dir -r requirements_animate.txt

# Install RunPod
RUN pip3 install runpod

# Copy handler
COPY handler.py /workspace/handler.py

# Set Python path
ENV PYTHONPATH="/workspace/Wan2.2:${PYTHONPATH}"

# Command
CMD ["python3", "-u", "/workspace/handler.py"]

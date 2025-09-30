#!/bin/bash
set -e

echo "=== Downloading ComfyUI Models ==="

# Source conda and activate environment
source "$HOME/miniforge3/etc/profile.d/conda.sh"
conda activate comfy-env

# Verify comfy CLI is available
if ! command -v comfy &> /dev/null; then
    echo "Error: comfy CLI not found. Please run setup_comfy_env.sh first."
    exit 1
fi

echo "Downloading Qwen Image VAE model..."
comfy model download \
    --url https://huggingface.co/Comfy-Org/Qwen-Image_ComfyUI/resolve/main/split_files/vae/qwen_image_vae.safetensors \
    --relative-path comfy/ComfyUI/models/vae \
    --filename qwen_image_vae.safetensors

echo "Downloading Qwen 2.5 VL text encoder model..."
comfy model download \
    --url https://huggingface.co/Comfy-Org/Qwen-Image_ComfyUI/resolve/main/split_files/text_encoders/qwen_2.5_vl_7b_fp8_scaled.safetensors \
    --relative-path comfy/ComfyUI/models/text_encoders \
    --filename qwen_2.5_vl_7b_fp8_scaled.safetensors

echo "Downloading Qwen Image diffusion model..."
comfy model download \
    --url https://huggingface.co/Comfy-Org/Qwen-Image_ComfyUI/resolve/main/split_files/diffusion_models/qwen_image_fp8_e4m3fn.safetensors \
    --relative-path comfy/ComfyUI/models/diffusion_models \
    --filename qwen_image_fp8_e4m3fn.safetensors

echo "Downloading Wan2.2 5B hybrid model (text-to-video and image-to-video)..."
comfy model download \
    --url https://huggingface.co/Comfy-Org/Wan_2.2_ComfyUI_Repackaged/resolve/main/split_files/diffusion_models/wan2.2_ti2v_5B_fp16.safetensors \
    --relative-path comfy/ComfyUI/models/diffusion_models \
    --filename wan2.2_ti2v_5B_fp16.safetensors

echo "Downloading Wan2.2 VAE model..."
comfy model download \
    --url https://huggingface.co/Comfy-Org/Wan_2.2_ComfyUI_Repackaged/resolve/main/split_files/vae/wan2.2_vae.safetensors \
    --relative-path comfy/ComfyUI/models/vae \
    --filename wan2.2_vae.safetensors

echo "Downloading UMT5 text encoder for Wan2.2..."
comfy model download \
    --url https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors \
    --relative-path comfy/ComfyUI/models/text_encoders \
    --filename umt5_xxl_fp8_e4m3fn_scaled.safetensors

echo "=== Model downloads complete ==="
echo "Models saved to comfy/ComfyUI/models/"
echo ""
echo "Available models:"
echo "  Qwen Image: For image generation workflows"
echo "  Wan2.2 5B: For video generation (text-to-video and image-to-video, fits 8GB VRAM)"
#!/bin/bash
set -e

echo "=== Enhanced ComfyUI Model Download Script ==="
echo "Downloads Qwen-Image, Qwen-Image-Edit, Wan2.2 models and workflows"
echo ""

# Source conda and activate environment
source "$HOME/miniforge3/etc/profile.d/conda.sh"
conda activate comfy-env

# Verify comfy CLI is available
if ! command -v comfy &> /dev/null; then
    echo "Error: comfy CLI not found. Please run setup_comfy_env.sh first."
    exit 1
fi

# Create workflow directory if it doesn't exist
WORKFLOW_DIR="comfy/ComfyUI/user/default/workflows"
mkdir -p "$WORKFLOW_DIR"

# ===================================
# SECTION 1: QWEN-IMAGE BASE MODELS
# ===================================
echo ""
echo "=== Section 1: Qwen-Image Base Models ==="

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

echo "Downloading Qwen Image diffusion model (FP8)..."
comfy model download \
    --url https://huggingface.co/Comfy-Org/Qwen-Image_ComfyUI/resolve/main/split_files/diffusion_models/qwen_image_fp8_e4m3fn.safetensors \
    --relative-path comfy/ComfyUI/models/diffusion_models \
    --filename qwen_image_fp8_e4m3fn.safetensors

# ===================================
# SECTION 2: QWEN-IMAGE LIGHTNING LORAS
# ===================================
echo ""
echo "=== Section 2: Qwen-Image Lightning LoRAs ==="

echo "Downloading Qwen-Image Lightning 4-step LoRA v1.0..."
comfy model download \
    --url https://huggingface.co/lightx2v/Qwen-Image-Lightning/resolve/main/Qwen-Image-Lightning-4steps-V1.0.safetensors \
    --relative-path comfy/ComfyUI/models/loras \
    --filename Qwen-Image-Lightning-4steps-V1.0.safetensors

echo "Downloading Qwen-Image Lightning 8-step LoRA v1.1 (latest)..."
comfy model download \
    --url https://huggingface.co/lightx2v/Qwen-Image-Lightning/resolve/main/Qwen-Image-Lightning-8steps-V1.1.safetensors \
    --relative-path comfy/ComfyUI/models/loras \
    --filename Qwen-Image-Lightning-8steps-V1.1.safetensors

# ===================================
# SECTION 3: QWEN-IMAGE-EDIT MODELS
# ===================================
echo ""
echo "=== Section 3: Qwen-Image-Edit Models ==="

echo "Downloading Qwen-Image-Edit diffusion model (FP8)..."
comfy model download \
    --url https://huggingface.co/Comfy-Org/Qwen-Image-Edit_ComfyUI/resolve/main/split_files/diffusion_models/qwen_image_edit_fp8_e4m3fn.safetensors \
    --relative-path comfy/ComfyUI/models/diffusion_models \
    --filename qwen_image_edit_fp8_e4m3fn.safetensors

echo "Downloading Qwen-Image-Edit Lightning 4-step LoRA..."
comfy model download \
    --url https://huggingface.co/lightx2v/Qwen-Image-Lightning/resolve/main/Qwen-Image-Edit-Lightning-4steps-V1.0.safetensors \
    --relative-path comfy/ComfyUI/models/loras \
    --filename Qwen-Image-Edit-Lightning-4steps-V1.0.safetensors

echo "Downloading Qwen-Image-Edit Lightning 8-step LoRA..."
comfy model download \
    --url https://huggingface.co/lightx2v/Qwen-Image-Lightning/resolve/main/Qwen-Image-Edit-Lightning-8steps-V1.0.safetensors \
    --relative-path comfy/ComfyUI/models/loras \
    --filename Qwen-Image-Edit-Lightning-8steps-V1.0.safetensors

# ===================================
# SECTION 4: WAN 2.2 BASE MODELS
# ===================================
echo ""
echo "=== Section 4: Wan 2.2 Base Models ==="

# Use Kijai's working repository for Wan 2.2 models (correct URLs)
echo "Downloading Wan2.2 14B T2V model..."
comfy model download \
    --url https://huggingface.co/Kijai/WanVideo_comfy_fp8_scaled/resolve/main/I2V/Wan2_2-I2V-A14B-HIGH_fp8_e5m2_scaled_KJ.safetensors \
    --relative-path comfy/ComfyUI/models/diffusion_models \
    --filename Wan2_2-I2V-A14B-HIGH_fp8_e5m2_scaled_KJ.safetensors

comfy model download \
    --url https://huggingface.co/Kijai/WanVideo_comfy_fp8_scaled/resolve/main/I2V/Wan2_2-I2V-A14B-LOW_fp8_e5m2_scaled_KJ.safetensors \
    --relative-path comfy/ComfyUI/models/diffusion_models \
    --filename Wan2_2-I2V-A14B-LOW_fp8_e5m2_scaled_KJ.safetensors


# Wan VAE (shared across versions)
echo "Downloading Wan VAE model..."
comfy model download \
    --url https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/vae/wan_2.1_vae.safetensors \
    --relative-path comfy/ComfyUI/models/vae \
    --filename wan_2.1_vae.safetensors

# UMT5 text encoder
echo "Downloading UMT5 text encoder..."
comfy model download \
    --url https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors \
    --relative-path comfy/ComfyUI/models/text_encoders \
    --filename umt5_xxl_fp8_e4m3fn_scaled.safetensors

# ===================================
# LIGHTX2V LORAS (Speed boost)
# ===================================
echo ""
echo "=== LightX2V LoRAs for Wan 2.2 ==="

echo "Downloading Wan2.2 I2V LightX2V 4-step LoRA..."
comfy model download \
    --url https://huggingface.co/Comfy-Org/Wan_2.2_ComfyUI_Repackaged/resolve/main/split_files/loras/wan2.2_i2v_lightx2v_4steps_lora_v1_high_noise.safetensors \
    --relative-path comfy/ComfyUI/models/loras \
    --filename wan2.2_i2v_lightx2v_4steps_lora_v1_high_noise.safetensors

echo "Downloading Wan2.2 T2V LightX2V 4-step LoRA..."
comfy model download \
    --url https://huggingface.co/Comfy-Org/Wan_2.2_ComfyUI_Repackaged/resolve/main/split_files/loras/wan2.2_t2v_lightx2v_4steps_lora_v1.1_high_noise.safetensors \
    --relative-path comfy/ComfyUI/models/loras \
    --filename wan2.2_t2v_lightx2v_4steps_lora_v1.1_high_noise.safetensors

# ===================================
# DOWNLOAD WORKFLOW JSON FILES
# ===================================
echo ""
echo "=== Downloading Workflow JSON Files ==="

# Download Qwen-Image workflows
echo "Downloading Qwen-Image Lightning workflows..."
wget -q -O "$WORKFLOW_DIR/qwen-image-lightning-4steps.json" \
    "https://raw.githubusercontent.com/ModelTC/Qwen-Image-Lightning/main/workflows/qwen-image-4steps.json"

wget -q -O "$WORKFLOW_DIR/qwen-image-lightning-8steps.json" \
    "https://raw.githubusercontent.com/ModelTC/Qwen-Image-Lightning/main/workflows/qwen-image-8steps.json"

# Download Qwen-Image-Edit workflows
echo "Downloading Qwen-Image-Edit Lightning workflows..."
wget -q -O "$WORKFLOW_DIR/qwen-image-edit-lightning-4steps.json" \
    "https://raw.githubusercontent.com/ModelTC/Qwen-Image-Lightning/main/workflows/qwen-image-edit-4steps.json"

wget -q -O "$WORKFLOW_DIR/qwen-image-edit-lightning-8steps.json" \
    "https://raw.githubusercontent.com/ModelTC/Qwen-Image-Lightning/main/workflows/qwen-image-edit-8steps.json"

# Download basic Qwen workflows from ComfyUI examples
echo "Downloading basic Qwen workflows..."
wget -q -O "$WORKFLOW_DIR/qwen-image-basic.json" \
    "https://comfyanonymous.github.io/ComfyUI_examples/qwen_image/qwen_image_workflow.json" || echo "Basic workflow download failed, skipping..."

wget -q -O "$WORKFLOW_DIR/qwen-image-edit-basic.json" \
    "https://comfyanonymous.github.io/ComfyUI_examples/qwen_image/qwen_image_edit_workflow.json" || echo "Edit workflow download failed, skipping..."

# Create example Wan 2.2 workflow JSON
echo "Creating example Wan 2.2 workflow..."
cat > "$WORKFLOW_DIR/wan2.2-i2v-example.json" << 'EOF'
{
  "last_node_id": 10,
  "last_link_id": 15,
  "nodes": [
    {
      "id": 1,
      "type": "LoadImage",
      "pos": [100, 100],
      "size": [300, 150],
      "outputs": [{"name": "IMAGE", "type": "IMAGE"}],
      "properties": {"Node name for S&R": "LoadImage"},
      "widgets_values": ["input_image.png"]
    },
    {
      "id": 2,
      "type": "LoadDiffusionModel",
      "pos": [100, 300],
      "outputs": [{"name": "MODEL", "type": "MODEL"}],
      "properties": {"Node name for S&R": "LoadDiffusionModel"},
      "widgets_values": ["wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors", "diffusers"]
    },
    {
      "id": 3,
      "type": "CLIPLoader",
      "pos": [100, 450],
      "outputs": [{"name": "CLIP", "type": "CLIP"}],
      "properties": {"Node name for S&R": "CLIPLoader"},
      "widgets_values": ["umt5_xxl_fp8_e4m3fn_scaled.safetensors", "stable_cascade", "umt5", "fp16"]
    },
    {
      "id": 4,
      "type": "VAELoader",
      "pos": [100, 600],
      "outputs": [{"name": "VAE", "type": "VAE"}],
      "properties": {"Node name for S&R": "VAELoader"},
      "widgets_values": ["wan_2.1_vae.safetensors"]
    },
    {
      "id": 5,
      "type": "CLIPTextEncode",
      "pos": [450, 450],
      "inputs": [{"name": "clip", "type": "CLIP", "link": 10}],
      "outputs": [{"name": "CONDITIONING", "type": "CONDITIONING"}],
      "properties": {"Node name for S&R": "CLIPTextEncode"},
      "widgets_values": ["A beautiful sunset over mountains, cinematic lighting"]
    }
  ],
  "links": [],
  "version": 0.4
}
EOF

# Create Qwen-Image Lightning example workflow
echo "Creating Qwen-Image Lightning example workflow..."
cat > "$WORKFLOW_DIR/qwen-image-lightning-example.json" << 'EOF'
{
  "last_node_id": 8,
  "last_link_id": 12,
  "nodes": [
    {
      "id": 1,
      "type": "LoadDiffusionModel",
      "pos": [50, 100],
      "outputs": [{"name": "MODEL", "type": "MODEL"}],
      "properties": {"Node name for S&R": "LoadDiffusionModel"},
      "widgets_values": ["qwen_image_fp8_e4m3fn.safetensors", "diffusers"]
    },
    {
      "id": 2,
      "type": "LoraLoaderModelOnly",
      "pos": [350, 100],
      "inputs": [{"name": "model", "type": "MODEL", "link": 1}],
      "outputs": [{"name": "MODEL", "type": "MODEL"}],
      "properties": {"Node name for S&R": "LoraLoaderModelOnly"},
      "widgets_values": ["Qwen-Image-Lightning-8steps-V1.1.safetensors", 1.0]
    },
    {
      "id": 3,
      "type": "CLIPLoader",
      "pos": [50, 250],
      "outputs": [{"name": "CLIP", "type": "CLIP"}],
      "properties": {"Node name for S&R": "CLIPLoader"},
      "widgets_values": ["qwen_2.5_vl_7b_fp8_scaled.safetensors", "stable_cascade", "qwen", "fp16"]
    },
    {
      "id": 4,
      "type": "VAELoader",
      "pos": [50, 400],
      "outputs": [{"name": "VAE", "type": "VAE"}],
      "properties": {"Node name for S&R": "VAELoader"},
      "widgets_values": ["qwen_image_vae.safetensors"]
    },
    {
      "id": 5,
      "type": "KSampler",
      "pos": [650, 200],
      "inputs": [
        {"name": "model", "type": "MODEL", "link": 2},
        {"name": "positive", "type": "CONDITIONING", "link": 8},
        {"name": "negative", "type": "CONDITIONING", "link": 9},
        {"name": "latent_image", "type": "LATENT", "link": 10}
      ],
      "outputs": [{"name": "LATENT", "type": "LATENT"}],
      "properties": {"Node name for S&R": "KSampler"},
      "widgets_values": [42, "fixed", 8, 1.0, "euler", "normal", 1.0]
    }
  ],
  "links": [],
  "version": 0.4
}
EOF

echo ""
echo "=== Model downloads complete ==="
echo ""
echo "Downloaded models summary:"
echo "-------------------------"
echo "✓ Qwen-Image: Base model + Lightning LoRAs (4-step, 8-step v1.0 & v1.1)"
echo "✓ Qwen-Image-Edit: Base model + Lightning LoRAs"
echo "✓ Wan 2.2: I2V models (14B)"
echo "✓ LightX2V: 4-step LoRAs for faster generation"
echo "✓ Workflows: Multiple JSON workflow files in $WORKFLOW_DIR"
echo ""
echo "Models saved to:"
echo "  • Diffusion models: comfy/ComfyUI/models/diffusion_models/"
echo "  • VAE models: comfy/ComfyUI/models/vae/"
echo "  • Text encoders: comfy/ComfyUI/models/text_encoders/"
echo "  • LoRA models: comfy/ComfyUI/models/loras/"
echo "  • Workflows: $WORKFLOW_DIR/"
echo ""
echo "Usage tips:"
echo "-----------"
echo "• Qwen-Image Lightning: Use 4-step or 8-step LoRAs for 6-12x faster generation"
echo "• Qwen-Image-Edit 2509: Latest version with better consistency"
echo "• Wan 2.2 Animate: For character animation and motion replication"
echo "• Wan 2.2 Fun: InP for first-last frame control, Control for multi-modal guidance"
echo "• LightX2V LoRAs: Reduce Wan 2.2 generation to just 4 steps"
echo ""
echo "Recommended VRAM requirements:"
echo "• Qwen models (FP8): 12-16GB VRAM"
echo "• Wan 2.2 5B: 8-12GB VRAM"
echo "• Wan 2.2 14B: 16-24GB VRAM"
echo "• With Lightning/LightX2V LoRAs: Can reduce VRAM by ~20-30%"
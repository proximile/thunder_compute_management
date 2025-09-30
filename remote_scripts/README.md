# Remote Scripts

This directory contains scripts for setting up software environments on remote ThunderCompute instances.

## Scripts

### `install_miniforge.sh`
Installs Miniforge conda distribution:
- Removes any existing miniconda3/miniforge3 installations
- Downloads and installs latest Miniforge
- Initializes conda for bash
- Cleans up installer files

### `setup_comfy_env.sh` 
Sets up ComfyUI environment:
- Creates `comfy-env` conda environment with Python 3.11
- Installs comfy-cli package
- Verifies installation

### `download_comfy_models.sh`
Downloads ComfyUI models:
- Downloads Qwen Image VAE model
- Downloads Qwen 2.5 VL text encoder model
- Saves to appropriate ComfyUI model directories

### `full_setup.sh`
Runs complete setup:
- Executes all above scripts in sequence
- Handles environment sourcing between steps
- Provides final usage instructions

### `install_cloudflared.sh`
Installs Cloudflare Tunnel (cloudflared):
- Downloads latest cloudflared .deb package
- Installs via apt package manager
- Handles dependency resolution
- Verifies installation

### `run_cloudflare_tunnel.sh`
Runs Cloudflare tunnel in foreground:
- Creates TryCloudflare tunnel for specified port (default: 8188)
- Generates random subdomain on trycloudflare.com
- Validates port number input
- Runs in foreground (Ctrl+C to stop)

### `start_tunnel_background.sh`
Runs Cloudflare tunnel in background:
- Creates tunnel in detached tmux session
- Default port 8188, customizable session name
- Provides commands to view/manage tunnel
- Non-blocking execution

## Usage

### Using ThunderComputeManager

```python
from thunder_compute_manager import ThunderComputeManager

manager = ThunderComputeManager.from_secrets()
instance_id = 12345

# Upload all scripts
manager.upload_directory(instance_id, "./remote_scripts", "/home/ubuntu/remote_scripts")

# Make scripts executable
ssh = manager.connect_ssh(instance_id)
ssh.exec_command("chmod +x /home/ubuntu/remote_scripts/*.sh")

# Run full setup
manager.start_tmux_session(instance_id, "setup")
manager.run_script_in_tmux(instance_id, "setup", "/home/ubuntu/remote_scripts/full_setup.sh", 
                          wait_for_completion=True, wait_timeout=1800)

# Check results
output = manager.get_tmux_output(instance_id, "setup")
print(output)
```

### Manual Usage

Upload scripts to remote instance and run:

```bash
# Make executable
chmod +x remote_scripts/*.sh

# Run individual scripts
./remote_scripts/install_miniforge.sh
source ~/.bashrc
./remote_scripts/setup_comfy_env.sh
./remote_scripts/download_comfy_models.sh

# Or run full setup
./remote_scripts/full_setup.sh

# Install and setup Cloudflare tunnels
./remote_scripts/install_cloudflared.sh

# Run tunnel in foreground (default port 8188)
./remote_scripts/run_cloudflare_tunnel.sh

# Run tunnel for specific port
./remote_scripts/run_cloudflare_tunnel.sh 3000

# Run tunnel in background tmux session
./remote_scripts/start_tunnel_background.sh 8188 my-tunnel

# View background tunnel
tmux attach -t my-tunnel
```

## Cloudflare Tunnel Usage

After installing cloudflared, you can create tunnels to expose local services:

```bash
# Start your local service (e.g., ComfyUI)
conda activate comfy-env
comfy ui --port 8188

# In another terminal/tmux session, start tunnel
./remote_scripts/run_cloudflare_tunnel.sh 8188
```

The tunnel will provide a public URL like `https://random-subdomain.trycloudflare.com` that forwards to your local service.

### Using with ThunderComputeManager

```python
# Upload cloudflared scripts
manager.upload_directory(instance_id, "./remote_scripts", "/home/ubuntu/remote_scripts")

# Install cloudflared
manager.run_script_in_tmux(instance_id, "setup", "/home/ubuntu/remote_scripts/install_cloudflared.sh")

# Start tunnel in background (assuming service on port 8188)
manager.run_script_in_tmux(instance_id, "tunnel", "/home/ubuntu/remote_scripts/start_tunnel_background.sh")

# Get tunnel URL from tmux output
import time
time.sleep(5)  # Wait for tunnel to establish
tunnel_output = manager.get_tmux_output(instance_id, "cloudflare-tunnel")
print("Tunnel output:", tunnel_output)
```

## Requirements

- Ubuntu/Debian-based system
- Internet connection for downloads
- Sufficient disk space (~2-3GB for models)

## Notes

- Scripts use `set -e` for error handling
- Miniforge installation is non-interactive (`-b` flag)
- Models are downloaded to `~/comfy/ComfyUI/models/`
- Environment name is `comfy-env`
- Scripts handle cleanup of previous installations
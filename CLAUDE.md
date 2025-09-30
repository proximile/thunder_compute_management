# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Thunder Compute Management is a Python library that provides programmatic control over ThunderCompute cloud instances. It enables instance lifecycle management, SSH connectivity with automatic key handling, file transfers, and tmux session management for remote development workflows.

## Core Architecture

### ThunderComputeManager Class
The main class `ThunderComputeManager` (`thunder_compute_manager.py:13`) provides comprehensive instance management capabilities:

- **API Integration**: REST API client for ThunderCompute services
- **SSH Management**: Per-instance SSH key handling with automatic setup
- **Connection Caching**: Persistent SSH connections with health checking
- **Instance Lifecycle**: Create, start, stop, modify, delete, and clone operations
- **File Operations**: Upload/download files and directories with permission preservation
- **Remote Execution**: tmux session management for long-running remote processes

### Key Components

**Instance Management** (`thunder_compute_manager.py:183-253`):
- `list_instances()` - Get all instances with caching (30s TTL)
- `get_instance_info()` - Retrieve specific instance details
- `start_instance()` / `stop_instance()` - Control instance state
- `wait_for_status()` - Poll for instance state changes

**SSH Connectivity** (`thunder_compute_manager.py:254-343`):
- Per-instance SSH key management in `./secrets/` directory
- Automatic key extraction from `~/.ssh/config` via `tnr connect` command
- Connection pooling and health checking
- Support for RSA, ECDSA, and Ed25519 keys

**File Transfer** (`thunder_compute_manager.py:498-723`):
- `upload_file()` / `download_file()` - Single file operations
- `upload_directory()` / `download_directory()` - Recursive directory sync
- `sync_file()` - Timestamp-based synchronization
- Permission preservation and directory creation

**Remote Execution** (`thunder_compute_manager.py:353-461`):
- `start_tmux_session()` - Create persistent remote sessions
- `run_script_in_tmux()` - Execute scripts with optional completion tracking
- `get_tmux_output()` - Capture session output

## Usage Patterns

### Basic Instance Management
```python
# Auto-setup keys as needed
manager = ThunderComputeManager.from_secrets()

# List all instances
instances = manager.list_instances()

# Start instance and wait for ready state
manager.start_instance(12345)
manager.wait_for_status(12345, "RUNNING")

# Connect via SSH (auto-handles keys)
ssh = manager.connect_ssh(12345)
```

### File Operations
```python
# Upload single file
manager.upload_file(12345, "./local_script.py", "/home/ubuntu/script.py")

# Sync directory (only transfer changed files)
manager.sync_file(12345, "./local_file.txt", "/remote/file.txt", direction="upload")

# Download entire directory
manager.download_directory(12345, "/home/ubuntu/project", "./local_project")
```

### Remote Script Execution
```python
# Start tmux session and run script
manager.start_tmux_session(12345, "training")
manager.run_script_in_tmux(12345, "training", "/home/ubuntu/train.sh", 
                          wait_for_completion=True, wait_timeout=3600)

# Get output from session
output = manager.get_tmux_output(12345, "training")
```

### Instance Creation and Lifecycle
```python
# Create new instance
new_instance = manager.create_instance(
    cpu_cores=8,
    gpu_type="a100xl", 
    num_gpus=1,
    disk_size_gb=200,
    wait_for_running=True
)

# Clone existing instance with modifications
cloned = manager.clone_instance(
    source_instance_id=12345,
    cpu_cores=16,
    gpu_type="a100xl",
    num_gpus=2
)

# Modify running instance
manager.modify_instance(12345, cpu_cores=16, disk_size_gb=500)

# Delete instance (requires confirmation)
manager.delete_instance(12345, confirm=True)
```

## Development Environment

### Dependencies
- `requests` - HTTP API client
- `paramiko` - SSH client library
- `pathlib` - Path handling
- Standard library: `os`, `time`, `json`, `subprocess`, `shutil`, `stat`

### Secrets Management
The `./secrets/` directory structure:
- `api_key.txt` - ThunderCompute API authentication token
- `id_rsa_instance_{ID}` - Per-instance SSH private keys (600 permissions)

### SSH Integration
- Reads from `~/.ssh/config` for Thunder CLI entries (`tnr-{instance_id}`)
- Automatically runs `tnr connect {instance_id}` if SSH config missing
- Copies keys to local secrets directory for programmatic access
- Supports multiple concurrent instance connections

### Error Handling
- Comprehensive validation of API responses and SSH connectivity
- Automatic retry logic for connection failures
- Graceful handling of missing dependencies (Thunder CLI)
- Detailed error messages with troubleshooting guidance

## Common Development Tasks

### Running the Module
```bash
# Basic usage demonstration
python thunder_compute_manager.py

# Interactive testing
python -c "from thunder_compute_manager import ThunderComputeManager; manager = ThunderComputeManager.from_secrets(); print(manager.list_instances())"
```

### Key Management
```bash
# Setup SSH keys for all instances
python -c "from thunder_compute_manager import ThunderComputeManager; manager = ThunderComputeManager.from_secrets(); manager.setup_all_instance_keys()"

# Validate secrets configuration
python -c "from thunder_compute_manager import ThunderComputeManager; manager = ThunderComputeManager.from_secrets(); print(manager.validate_secrets_setup())"
```

### Testing Instance Operations
```bash
# Test instance connectivity
python -c "from thunder_compute_manager import ThunderComputeManager; manager = ThunderComputeManager.from_secrets(); ssh = manager.connect_ssh(INSTANCE_ID); print('Connected successfully')"
```

## Integration Notes

### Thunder CLI Dependency
- Requires Thunder CLI (`tnr` command) for initial SSH key setup
- Falls back gracefully if CLI unavailable with clear error messages
- Manual key management supported via `auto_setup_keys=False`

### Context Manager Support
```python
# Automatic connection cleanup
with ThunderComputeManager.from_secrets() as manager:
    ssh = manager.connect_ssh(12345)
    # Connections automatically closed on exit
```

### Factory Methods
- `ThunderComputeManager.from_secrets()` - Convenient setup with defaults
- `manager.validate_secrets_setup()` - Comprehensive configuration validation
- `manager.list_instance_keys()` - Inventory of available SSH keys

## Script Architecture

### Local Scripts (`local_scripts/`)
Python automation scripts that import `thunder_compute_manager` for specific tasks:

**Core Automation:**
- `full_setup.py` - Complete environment setup workflow (uploads remote scripts + executes full_setup.sh)
- `list_instances.py` - Instance inventory with filtering and detailed information
- `setup_comfy_instance.py` - Specialized ComfyUI environment setup with validation
- `start_tunnel.py` - Cloudflare tunnel management with URL extraction
- `start_comfy_with_tunnel.py` - Combined ComfyUI and tunnel startup with readiness detection

**Script Pattern:**
```python
# Standard structure for local scripts
sys.path.insert(0, str(Path(__file__).parent.parent))
from thunder_compute_manager import ThunderComputeManager

def main():
    with ThunderComputeManager.from_secrets() as manager:
        # Automation logic using manager
        pass
```

### Remote Scripts (`remote_scripts/`)
Bash scripts designed for execution on ThunderCompute instances:

**Environment Setup:**
- `install_miniforge.sh` - Conda distribution installation with cleanup
- `setup_comfy_env.sh` - ComfyUI environment creation (comfy-env with Python 3.11) and ComfyUI installation to `~/comfy/ComfyUI`
- `download_comfy_models.sh` - Qwen model downloads for ComfyUI
- `full_setup.sh` - Orchestrates complete setup sequence

**Tunnel Management:**
- `install_cloudflared.sh` - Cloudflare tunnel daemon installation
- `run_cloudflare_tunnel.sh` - Foreground tunnel execution (default port 8188)
- `start_tunnel_background.sh` - Background tunnel in tmux session

**Design Principles:**
- Non-interactive installation (`-b` flags, `-y` confirmations)
- Error handling with `set -e` for fail-fast behavior
- Cleanup of temporary files and previous installations
- Tmux integration for persistent background processes

## ComfyUI Integration

### Path Configuration
ComfyUI is installed to `~/comfy/ComfyUI` via the comfy CLI. All scripts reference this standard path:
- **Installation**: `comfy ui install` in `setup_comfy_env.sh`
- **Execution**: Scripts use `cd /home/ubuntu/comfy/ComfyUI` before starting ComfyUI
- **Models**: Downloaded to `~/comfy/ComfyUI/models/` subdirectories

### Ready State Detection
ComfyUI readiness is detected by monitoring tmux output for:
```
To see the GUI go to: http://0.0.0.0:8188
```

### Tunnel URL Extraction
Cloudflare tunnel URLs are extracted from the boxed message format:
```
| https://example-subdomain.trycloudflare.com |
```

### Output Management
- **Output Directory**: `./outputs/` (renamed from `tunnel_outputs/`)
- **Log Format**: Separate sections for tunnel and ComfyUI outputs with timestamps
- **File Naming**: `tunnel_output_instance_{ID}_{timestamp}.txt`

## Workflow Automation

### Complete Instance Setup
```bash
# Single command complete setup
python local_scripts/full_setup.py -i 12345

# Equivalent manual steps:
# 1. Upload all remote_scripts/ to /home/ubuntu/remote_scripts/
# 2. Make scripts executable
# 3. Execute full_setup.sh in tmux with timeout monitoring
# 4. Validate installation success
```

### Service Deployment Pattern
```python
# Common pattern for service deployment
manager = ThunderComputeManager.from_secrets()

# 1. Instance preparation
manager.start_instance(instance_id)
manager.wait_for_status(instance_id, "RUNNING")

# 2. Environment setup
manager.upload_directory(instance_id, "./remote_scripts", "/home/ubuntu/remote_scripts")
manager.run_script_in_tmux(instance_id, "setup", "/home/ubuntu/remote_scripts/full_setup.sh")

# 3. Service startup
manager.run_script_in_tmux(instance_id, "service", "/path/to/service_script.sh")

# 4. Tunnel exposure
manager.run_script_in_tmux(instance_id, "tunnel", "/home/ubuntu/remote_scripts/start_tunnel_background.sh")
```

### Common Automation Commands

```bash
# List and filter instances
python local_scripts/list_instances.py --status RUNNING
python local_scripts/list_instances.py --json

# Setup specific environments
python local_scripts/setup_comfy_instance.py -i 12345 --timeout 2400 -v

# Tunnel management
python local_scripts/start_tunnel.py -i 12345 -p 8188 --wait-for-url --install-cloudflared

# Combined ComfyUI and tunnel startup
python local_scripts/start_comfy_with_tunnel.py -i 12345 --wait-for-url --install-cloudflared -v

# Direct manager usage for custom workflows
python -c "
from thunder_compute_manager import ThunderComputeManager
manager = ThunderComputeManager.from_secrets()
# Custom automation logic
"
```
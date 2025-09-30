# Thunder Compute Management

A Python library for programmatic control of ThunderCompute cloud instances, providing comprehensive instance lifecycle management, SSH connectivity, file transfers, and remote execution capabilities.

## Features

- **Instance Management**: Create, start, stop, modify, delete, and clone ThunderCompute instances
- **Automatic SSH Setup**: Per-instance SSH key management with automatic extraction from Thunder CLI
- **File Operations**: Upload/download files and directories with sync capabilities
- **Remote Execution**: tmux session management for long-running remote processes
- **Connection Pooling**: Persistent SSH connections with health checking
- **Error Handling**: Comprehensive validation and retry logic

## Quick Start

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd thunder_compute_management

# Install dependencies
pip install requests paramiko
```

### Setup

1. **API Key**: Save your ThunderCompute API key in `./secrets/api_key.txt`
2. **SSH Keys**: The library will automatically setup SSH keys using Thunder CLI

### Basic Usage

```python
from thunder_compute_manager import ThunderComputeManager

# Create manager with automatic key setup
manager = ThunderComputeManager.from_secrets()

# List all instances
instances = manager.list_instances()
print(f"Found {len(instances)} instances")

# Start an instance and wait for it to be ready
instance_id = 12345
manager.start_instance(instance_id)
manager.wait_for_status(instance_id, "RUNNING")

# Connect via SSH (automatically handles keys)
ssh = manager.connect_ssh(instance_id)

# Upload a file
manager.upload_file(instance_id, "./local_script.py", "/home/ubuntu/script.py")

# Run a script in tmux
manager.start_tmux_session(instance_id, "training")
manager.run_script_in_tmux(instance_id, "training", "/home/ubuntu/script.py")

# Get output
output = manager.get_tmux_output(instance_id, "training")
print(output)

# Cleanup
manager.cleanup_ssh_connections()
```

## Advanced Usage

### Instance Creation and Management

```python
# Create a new instance with GPU
new_instance = manager.create_instance(
    cpu_cores=8,
    gpu_type="a100xl",
    num_gpus=1,
    disk_size_gb=200,
    wait_for_running=True
)

# Clone an existing instance with modifications
cloned = manager.clone_instance(
    source_instance_id=12345,
    cpu_cores=16,
    gpu_type="a100xl",
    num_gpus=2
)

# Modify a running instance
manager.modify_instance(12345, cpu_cores=16, disk_size_gb=500)

# Delete an instance (requires confirmation)
manager.delete_instance(12345, confirm=True)
```

### File Transfer and Synchronization

```python
# Upload directory recursively
manager.upload_directory(instance_id, "./local_project", "/home/ubuntu/project")

# Download directory
manager.download_directory(instance_id, "/home/ubuntu/results", "./results")

# Sync files (only transfer if newer)
manager.sync_file(instance_id, "./config.json", "/home/ubuntu/config.json", 
                 direction="upload")
```

### Remote Script Execution

```python
# Run script with environment variables
env = {"CUDA_VISIBLE_DEVICES": "0", "BATCH_SIZE": "32"}
manager.run_script_in_tmux(
    instance_id, 
    "training",
    "/home/ubuntu/train.sh",
    env=env,
    wait_for_completion=True,
    wait_timeout=3600
)

# Monitor progress
while True:
    output = manager.get_tmux_output(instance_id, "training")
    if "Training complete" in output:
        break
    time.sleep(30)
```

### Key Management

```python
# Setup keys for all instances
all_keys = manager.setup_all_instance_keys()

# Validate configuration
validation = manager.validate_secrets_setup()
print(json.dumps(validation, indent=2))

# List available keys
keys = manager.list_instance_keys()
print(f"Available keys: {list(keys.keys())}")
```

## Configuration

### Directory Structure

```
thunder_compute_management/
├── thunder_compute_manager.py    # Main library
├── secrets/
│   ├── api_key.txt              # ThunderCompute API key
│   ├── id_rsa_instance_12345    # SSH key for instance 12345
│   └── id_rsa_instance_67890    # SSH key for instance 67890
├── local_scripts/               # Python automation scripts
│   ├── full_setup.py           # Complete environment setup
│   ├── list_instances.py       # Instance management
│   ├── setup_comfy_instance.py # ComfyUI-specific setup
│   └── start_tunnel.py         # Cloudflare tunnel management
├── remote_scripts/             # Bash scripts for remote execution
│   ├── full_setup.sh          # Orchestrates complete setup
│   ├── install_miniforge.sh   # Conda installation
│   ├── setup_comfy_env.sh     # ComfyUI environment
│   ├── download_comfy_models.sh # Model downloads
│   ├── install_cloudflared.sh # Tunnel daemon
│   ├── run_cloudflare_tunnel.sh # Foreground tunnel
│   └── start_tunnel_background.sh # Background tunnel
└── README.md
```

### Environment Variables

The library supports these optional environment variables:

- `THUNDER_API_KEY`: Alternative to `./secrets/api_key.txt`
- `THUNDER_SECRETS_DIR`: Custom secrets directory path

### SSH Integration

The library integrates with Thunder CLI (`tnr` command):

1. Reads SSH configuration from `~/.ssh/config`
2. Automatically runs `tnr connect {instance_id}` if needed
3. Copies keys to local secrets directory for programmatic access
4. Supports multiple concurrent instance connections

## Error Handling

The library provides comprehensive error handling:

- **API Errors**: Detailed error messages with HTTP status codes
- **SSH Errors**: Connection retry logic and key validation
- **File Transfer**: Permission and path validation
- **Instance State**: Polling with timeout for state changes

## Context Manager Support

```python
# Automatic connection cleanup
with ThunderComputeManager.from_secrets() as manager:
    ssh = manager.connect_ssh(12345)
    # Upload files, run scripts, etc.
    # Connections automatically closed on exit
```

## Dependencies

- `requests` - HTTP API client for ThunderCompute REST API
- `paramiko` - SSH client library for secure connections
- `pathlib` - Modern path handling (Python 3.4+)

## Script Automation

### Local Scripts
Python automation scripts that use ThunderComputeManager for specific tasks:

```bash
# Complete environment setup (recommended)
python local_scripts/full_setup.py -i 12345

# List instances with filtering
python local_scripts/list_instances.py --status RUNNING
python local_scripts/list_instances.py --json

# Specialized ComfyUI setup
python local_scripts/setup_comfy_instance.py -i 12345 --timeout 2400 -v

# Cloudflare tunnel management
python local_scripts/start_tunnel.py -i 12345 -p 8188 --wait-for-url --install-cloudflared
```

### Remote Scripts
Bash scripts designed for execution on remote instances (uploaded automatically by local scripts):

- **Environment Setup**: `install_miniforge.sh`, `setup_comfy_env.sh`, `download_comfy_models.sh`
- **Tunnel Management**: `install_cloudflared.sh`, `run_cloudflare_tunnel.sh`, `start_tunnel_background.sh`
- **Orchestration**: `full_setup.sh` (runs complete setup sequence)

All scripts follow these principles:
- Non-interactive installation suitable for remote execution
- Comprehensive error handling with `set -e`
- Cleanup of temporary files and previous installations
- Integration with tmux for persistent background processes

## Requirements

- Python 3.7+
- ThunderCompute account with API access
- Thunder CLI (`tnr` command) for initial SSH setup (optional)

## License

See [LICENSE](LICENSE) file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## Support

For issues and questions:
1. Check the [CLAUDE.md](CLAUDE.md) file for development guidance
2. Review the comprehensive examples in the main module
3. Open an issue with detailed error messages and steps to reproduce
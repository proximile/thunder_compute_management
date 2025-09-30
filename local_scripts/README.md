# Local Scripts

This directory contains Python scripts that import and use the `thunder_compute_manager` module to perform specific ThunderCompute instance management tasks. Each script is designed to accomplish a particular action or workflow.

## Overview

These scripts provide ready-to-use automation for common ThunderCompute operations:
- Instance lifecycle management (create, start, stop, delete)
- Environment setup and software installation
- File synchronization and deployment
- Remote service management
- Development workflow automation

## Script Categories

### Instance Management
Scripts for managing instance lifecycle and configuration.

### Environment Setup
Scripts for installing and configuring software environments on remote instances.

### Development Workflows
Scripts for common development tasks like deploying code, running services, and monitoring.

### Utility Scripts
Helper scripts for maintenance, monitoring, and troubleshooting.

## Usage

All scripts assume:
1. `thunder_compute_manager.py` is in the parent directory or Python path
2. API key is configured in `./secrets/api_key.txt`
3. SSH keys are properly set up (auto-handled by ThunderComputeManager)

### Running Scripts

```bash
# From the repository root
python local_scripts/script_name.py

# Or make executable and run directly
chmod +x local_scripts/script_name.py
./local_scripts/script_name.py
```

### Common Parameters

Most scripts accept common parameters:
- `--instance-id` or `-i`: Target instance ID
- `--port` or `-p`: Port number for services
- `--dry-run`: Show what would be done without executing
- `--verbose` or `-v`: Enable verbose output

## Script Conventions

Each script follows these conventions:

1. **Imports**: Import `thunder_compute_manager` and required modules
2. **Argument Parsing**: Use `argparse` for command-line options
3. **Error Handling**: Comprehensive error handling with meaningful messages
4. **Logging**: Clear progress indication and status messages
5. **Cleanup**: Proper resource cleanup (SSH connections, etc.)
6. **Documentation**: Docstrings and help text for all functions

### Example Script Structure

```python
#!/usr/bin/env python3
"""
Script description and purpose.
"""

import argparse
import sys
from pathlib import Path

# Add parent directory to path for thunder_compute_manager import
sys.path.insert(0, str(Path(__file__).parent.parent))
from thunder_compute_manager import ThunderComputeManager

def main():
    parser = argparse.ArgumentParser(description="Script description")
    parser.add_argument("-i", "--instance-id", type=int, required=True,
                      help="ThunderCompute instance ID")
    parser.add_argument("-v", "--verbose", action="store_true",
                      help="Enable verbose output")
    args = parser.parse_args()
    
    try:
        with ThunderComputeManager.from_secrets() as manager:
            # Script logic here
            pass
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
```

## Dependencies

- Python 3.7+
- `thunder_compute_manager` module
- `requests` and `paramiko` (for ThunderComputeManager)
- Standard library modules: `argparse`, `sys`, `pathlib`, `json`, `time`

## Configuration

Scripts read configuration from:
- `../secrets/api_key.txt` - ThunderCompute API key
- `../secrets/id_rsa_instance_*` - SSH keys for instances
- Command-line arguments for instance-specific parameters
- Environment variables (if supported by specific scripts)

## Error Handling

All scripts implement:
- Graceful error handling with informative messages
- Proper cleanup of resources (SSH connections, temporary files)
- Exit codes: 0 for success, 1 for errors
- Validation of required parameters and dependencies

## Development

When creating new scripts:

1. **Copy the example structure** from an existing script
2. **Add specific functionality** for your use case
3. **Test thoroughly** with different instance states
4. **Document parameters** and expected behavior
5. **Handle edge cases** (instance not found, network issues, etc.)
6. **Add to this README** with a brief description

## Security Notes

- Scripts use the same security model as ThunderComputeManager
- SSH keys are managed automatically and stored securely
- API keys should never be hardcoded in scripts
- Always validate user input and instance IDs
- Use context managers for automatic resource cleanup
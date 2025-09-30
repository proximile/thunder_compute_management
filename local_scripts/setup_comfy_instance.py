#!/usr/bin/env python3
"""
Complete ComfyUI setup on a ThunderCompute instance.
Uploads scripts, installs miniforge, sets up ComfyUI environment, and downloads models.
"""

import argparse
import sys
import time
from pathlib import Path

# Add parent directory to path for thunder_compute_manager import
sys.path.insert(0, str(Path(__file__).parent.parent))
from thunder_compute_manager import ThunderComputeManager

def main():
    parser = argparse.ArgumentParser(description="Setup ComfyUI on ThunderCompute instance")
    parser.add_argument("-i", "--instance-id", type=int, required=True,
                      help="ThunderCompute instance ID")
    parser.add_argument("--skip-upload", action="store_true",
                      help="Skip uploading remote scripts (if already present)")
    parser.add_argument("--skip-models", action="store_true",
                      help="Skip downloading ComfyUI models")
    parser.add_argument("-v", "--verbose", action="store_true",
                      help="Enable verbose output")
    parser.add_argument("--timeout", type=int, default=1800,
                      help="Timeout for setup operations in seconds (default: 1800)")
    args = parser.parse_args()
    
    try:
        with ThunderComputeManager.from_secrets() as manager:
            instance_id = args.instance_id
            
            # Verify instance exists and is running
            print(f"Checking instance {instance_id}...")
            info = manager.get_instance_info(instance_id)
            print(f"Instance status: {info.get('status')}")
            
            if info.get('status') != 'RUNNING':
                print("Instance is not running. Starting instance...")
                manager.start_instance(instance_id)
                if not manager.wait_for_status(instance_id, "RUNNING", timeout=120):
                    print("Failed to start instance within 2 minutes")
                    sys.exit(1)
                print("Instance is now running")
            
            # Upload remote scripts if not skipping
            if not args.skip_upload:
                print("Uploading remote scripts...")
                scripts_dir = Path(__file__).parent.parent / "remote_scripts"
                manager.upload_directory(instance_id, str(scripts_dir), "/home/ubuntu/remote_scripts")
                
                # Make scripts executable
                ssh = manager.connect_ssh(instance_id)
                ssh.exec_command("chmod +x /home/ubuntu/remote_scripts/*.sh")
                print("Scripts uploaded and made executable")
            
            # Run full setup
            print("Starting ComfyUI setup (this may take 10-20 minutes)...")
            manager.start_tmux_session(instance_id, "comfy-setup", cwd="/home/ubuntu")
            
            manager.run_script_in_tmux(
                instance_id, 
                "comfy-setup", 
                "/home/ubuntu/remote_scripts/full_setup.sh",
                wait_for_completion=True,
                wait_timeout=args.timeout
            )
            
            # Get setup output
            setup_output = manager.get_tmux_output(instance_id, "comfy-setup")
            
            if args.verbose:
                print("\n=== Setup Output ===")
                print(setup_output)
                print("=== End Output ===\n")
            
            # Check if setup was successful
            if "Full setup complete" in setup_output:
                print("✓ ComfyUI setup completed successfully!")
                
                # Test conda and comfy installation
                print("Testing installation...")
                ssh = manager.connect_ssh(instance_id)
                
                # Test conda
                exit_code, out, err = ssh.exec_command("source ~/.bashrc && conda --version")
                if exit_code == 0:
                    print(f"✓ Conda installed: {out.strip()}")
                else:
                    print(f"✗ Conda test failed: {err}")
                
                # Test comfy CLI
                exit_code, out, err = ssh.exec_command("source ~/.bashrc && conda activate comfy-env && comfy --help")
                if exit_code == 0:
                    print("✓ ComfyUI CLI installed successfully")
                else:
                    print(f"✗ ComfyUI CLI test failed: {err}")
                
                print(f"\nInstance {instance_id} is ready for ComfyUI development!")
                print("To connect: conda activate comfy-env")
                
            else:
                print("✗ Setup may have failed. Check the output above.")
                if not args.verbose:
                    print("Run with --verbose to see full output")
                sys.exit(1)
                
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
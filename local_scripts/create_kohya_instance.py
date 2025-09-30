#!/usr/bin/env python3
"""
Create a new ThunderCompute instance tailored for Kohya_SS LoRA training.
This script creates the instance with optimal specs and runs complete setup.
"""

import argparse
import json
import sys
import time
from pathlib import Path

# Add parent directory to path for thunder_compute_manager import
sys.path.insert(0, str(Path(__file__).parent.parent))
from thunder_compute_manager import ThunderComputeManager

def main():
    parser = argparse.ArgumentParser(description="Create and setup Kohya_SS instance on ThunderCompute")
    parser.add_argument("--cpu-cores", type=int, default=8,
                      help="Number of CPU cores (default: 8)")
    parser.add_argument("--gpu-type", default="a100xl",
                      help="GPU type (default: a100xl)")
    parser.add_argument("--num-gpus", type=int, default=1,
                      help="Number of GPUs (default: 1)")
    parser.add_argument("--disk-size", type=int, default=200,
                      help="Disk size in GB (default: 200)")
    parser.add_argument("--setup-timeout", type=int, default=3600,
                      help="Timeout for full setup in seconds (default: 3600)")
    parser.add_argument("--skip-setup", action="store_true",
                      help="Only create instance, skip Kohya_SS setup")
    parser.add_argument("-v", "--verbose", action="store_true",
                      help="Show detailed output")
    parser.add_argument("--name", default=None,
                      help="Instance name (optional)")
    
    args = parser.parse_args()
    
    try:
        with ThunderComputeManager.from_secrets() as manager:
            # Create instance with Kohya_SS-optimized specs
            print("Creating ThunderCompute instance for Kohya_SS...")
            print(f"Specs: {args.cpu_cores} cores, {args.gpu_type} x{args.num_gpus}, {args.disk_size}GB disk")
            
            create_params = {
                "cpu_cores": args.cpu_cores,
                "gpu_type": args.gpu_type, 
                "num_gpus": args.num_gpus,
                "disk_size_gb": args.disk_size,
                "wait_for_running": True
            }
            
            if args.name:
                create_params["name"] = args.name
            
            instance_info = manager.create_instance(**create_params)
            # API returns uuid, key, identifier - the identifier is the instance ID
            instance_id = instance_info["identifier"]
            
            print(f"✅ Instance created successfully!")
            print(f"Instance ID: {instance_id}")
            print(f"Status: {instance_info.get('status')}")
            
            if args.skip_setup:
                print("\nSkipping setup as requested.")
                print(f"To setup Kohya_SS later, run:")
                print(f"  python local_scripts/setup_kohya_instance_complete.py -i {instance_id}")
                return
            
            # Wait for SSH to be available with retry logic
            print("Waiting for SSH to be available...")
            max_retries = 12  # 2 minutes total
            for attempt in range(max_retries):
                try:
                    print(f"Attempting SSH connection (attempt {attempt + 1}/{max_retries})...")
                    ssh = manager.connect_ssh(instance_id)
                    # Test the connection
                    manager._run_ssh_command(ssh, "echo 'SSH ready'")
                    print("SSH connection established!")
                    break
                except Exception as e:
                    if attempt < max_retries - 1:
                        print(f"SSH not ready yet, waiting 10s... ({e})")
                        time.sleep(10)
                    else:
                        print(f"SSH connection failed after {max_retries} attempts")
                        raise
            
            # Run complete Kohya_SS setup
            print(f"\nStarting Kohya_SS setup (timeout: {args.setup_timeout}s)...")
            print("This will install:")
            print("  - System dependencies (Python 3.11, Git)")
            print("  - CUDA 12.8 toolkit")
            print("  - Miniforge conda distribution")
            print("  - Kohya_SS training environment")
            print("  - Cloudflare tunnel for external access")
            
            # Upload all remote scripts
            print("Uploading setup scripts...")
            scripts_dir = Path(__file__).parent.parent / "remote_scripts"
            manager.upload_directory(instance_id, str(scripts_dir), "/home/ubuntu/remote_scripts")
            
            # Make scripts executable and install tmux
            ssh = manager.connect_ssh(instance_id)
            print("Installing tmux and making scripts executable...")
            
            # Install tmux with proper error checking
            exit_code, out, err = manager._run_ssh_command(ssh, "sudo apt update && sudo apt install -y tmux")
            if exit_code != 0:
                print(f"❌ Failed to install tmux: {err}")
                raise RuntimeError(f"tmux installation failed: {err}")
            print("✅ tmux installed successfully")
            
            # Make scripts executable
            exit_code, out, err = manager._run_ssh_command(ssh, "chmod +x /home/ubuntu/remote_scripts/*.sh")
            if exit_code != 0:
                print(f"❌ Failed to make scripts executable: {err}")
                raise RuntimeError(f"chmod failed: {err}")
            print("✅ Scripts made executable")
            
            # Start tmux session and run full setup
            session_name = "kohya-setup"
            manager.start_tmux_session(instance_id, session_name, cwd="/home/ubuntu")
            
            # Execute full_setup_kohya.sh
            manager.run_script_in_tmux(
                instance_id,
                session_name,
                "/home/ubuntu/remote_scripts/full_setup_kohya.sh",
                wait_for_completion=True,
                wait_timeout=args.setup_timeout
            )
            
            # Get and check setup output
            output = manager.get_tmux_output(instance_id, session_name)
            
            if args.verbose:
                print("\n" + "="*60)
                print("SETUP OUTPUT")
                print("="*60)
                print(output)
                print("="*60 + "\n")
            
            # Check setup success
            if "Full Kohya_SS setup complete" in output:
                print("✅ Kohya_SS setup completed successfully!")
                print(f"\nInstance {instance_id} is ready for LoRA training!")
                
                print("\nNext steps:")
                print(f"  1. Start Kohya_SS GUI: cd /home/ubuntu/kohya_ss && ./gui.sh --listen 0.0.0.0 --server_port 7860")
                print(f"  2. Or with tunnel: python local_scripts/start_tunnel.py -i {instance_id} -p 7860")
                print(f"  3. SSH manually: tnr connect {instance_id}")
                
                print(f"\nInstance Details:")
                print(f"  Instance ID: {instance_id}")
                print(f"  CPU Cores: {args.cpu_cores}")
                print(f"  GPU: {args.gpu_type} x{args.num_gpus}")
                print(f"  Disk: {args.disk_size}GB")
                print(f"  Kohya_SS Path: /home/ubuntu/kohya_ss")
                print(f"  GUI Port: 7860")
                
            else:
                print("❌ Setup encountered issues")
                print("Check output above or run with --verbose for details")
                
                if not args.verbose:
                    print("\nLast lines of setup output:")
                    lines = output.strip().split('\n')
                    for line in lines[-10:]:
                        print(f"  {line}")
                
                print(f"\nTo debug:")
                print(f"  tnr connect {instance_id}")
                print(f"  tmux attach -t {session_name}")
                sys.exit(1)
                
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
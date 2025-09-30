#!/usr/bin/env python3
"""
Copy all remote_scripts to a ThunderCompute instance and execute full_setup_kohya.sh.
This sets up the complete Kohya_SS environment: system deps, CUDA, Kohya_SS, and tunneling.
"""

import argparse
import sys
import time
from pathlib import Path

# Add parent directory to path for thunder_compute_manager import
sys.path.insert(0, str(Path(__file__).parent.parent))
from thunder_compute_manager import ThunderComputeManager

def main():
    parser = argparse.ArgumentParser(description="Run full Kohya_SS setup on ThunderCompute instance")
    parser.add_argument("-i", "--instance-id", type=int, required=True,
                      help="ThunderCompute instance ID")
    parser.add_argument("--timeout", type=int, default=3600,
                      help="Timeout for setup in seconds (default: 3600)")
    parser.add_argument("-v", "--verbose", action="store_true",
                      help="Show detailed output")
    parser.add_argument("--session-name", default="kohya-setup",
                      help="Tmux session name (default: kohya-setup)")
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
            
            # Upload all remote scripts
            print("Uploading remote scripts to instance...")
            scripts_dir = Path(__file__).parent.parent / "remote_scripts"
            manager.upload_directory(instance_id, str(scripts_dir), "/home/ubuntu/remote_scripts")
            
            # Make all scripts executable
            print("Making scripts executable...")
            ssh = manager.connect_ssh(instance_id)
            exit_code, out, err = ssh.exec_command("chmod +x /home/ubuntu/remote_scripts/*.sh")
            if exit_code != 0:
                print(f"Warning: Failed to make scripts executable: {err}")
            
            print("Scripts uploaded successfully")
            
            # Start tmux session and run full setup
            print(f"Starting Kohya_SS setup in tmux session '{args.session_name}'...")
            print("This will install system dependencies, CUDA 12.8, and Kohya_SS")
            print(f"Estimated time: 20-40 minutes (timeout: {args.timeout}s)")
            
            manager.start_tmux_session(instance_id, args.session_name, cwd="/home/ubuntu")
            
            # Execute full_setup_kohya.sh
            manager.run_script_in_tmux(
                instance_id,
                args.session_name,
                "/home/ubuntu/remote_scripts/full_setup_kohya.sh",
                wait_for_completion=True,
                wait_timeout=args.timeout
            )
            
            # Get and display output
            print("\nRetrieving setup output...")
            output = manager.get_tmux_output(instance_id, args.session_name)
            
            if args.verbose:
                print("\n" + "="*60)
                print("FULL KOHYA_SS SETUP OUTPUT")
                print("="*60)
                print(output)
                print("="*60 + "\n")
            
            # Check if setup completed successfully
            if "Full Kohya_SS setup complete" in output:
                print("✅ Kohya_SS setup completed successfully!")
                print("\nWhat was installed:")
                print("  ✓ System dependencies (Python 3.11, Git)")
                print("  ✓ CUDA 12.8 toolkit")
                print("  ✓ Miniforge conda distribution")
                print("  ✓ Kohya_SS training environment")
                print("  ✓ Cloudflare tunnel for external access")
                
                print(f"\nTo use Kohya_SS on instance {instance_id}:")
                print("  1. SSH to instance: tnr connect {instance_id}")
                print("  2. Navigate to Kohya: cd /home/ubuntu/kohya_ss")
                print("  3. Start GUI: ./gui.sh --listen 0.0.0.0 --server_port 7860")
                print("  4. Access via tunnel or direct connection on port 7860")
                
            else:
                print("❌ Setup may have encountered issues")
                print("Check the output above or run with --verbose for full details")
                
                if not args.verbose:
                    print("\nLast few lines of output:")
                    lines = output.strip().split('\n')
                    for line in lines[-10:]:
                        print(f"  {line}")
                
                print(f"\nTo debug, connect to tmux session:")
                print(f"  tmux attach -t {args.session_name}")
                sys.exit(1)
                
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
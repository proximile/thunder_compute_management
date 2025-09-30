#!/usr/bin/env python3
"""
Start a Cloudflare tunnel on a ThunderCompute instance to expose a local service.
"""

import argparse
import sys
import time
import re
from pathlib import Path

# Add parent directory to path for thunder_compute_manager import
sys.path.insert(0, str(Path(__file__).parent.parent))
from thunder_compute_manager import ThunderComputeManager

def extract_tunnel_url(output):
    """Extract tunnel URL from cloudflared output."""
    # Look for patterns like https://something.trycloudflare.com
    pattern = r'https://[a-zA-Z0-9-]+\.trycloudflare\.com'
    matches = re.findall(pattern, output)
    return matches[-1] if matches else None

def main():
    parser = argparse.ArgumentParser(description="Start Cloudflare tunnel on ThunderCompute instance")
    parser.add_argument("-i", "--instance-id", type=int, required=True,
                      help="ThunderCompute instance ID")
    parser.add_argument("-p", "--port", type=int, default=8188,
                      help="Local port to tunnel (default: 8188)")
    parser.add_argument("--session-name", default="cloudflare-tunnel",
                      help="Tmux session name (default: cloudflare-tunnel)")
    parser.add_argument("--install-cloudflared", action="store_true",
                      help="Install cloudflared first if not present")
    parser.add_argument("--wait-for-url", action="store_true",
                      help="Wait and extract the tunnel URL")
    parser.add_argument("-v", "--verbose", action="store_true",
                      help="Enable verbose output")
    args = parser.parse_args()
    
    try:
        with ThunderComputeManager.from_secrets() as manager:
            instance_id = args.instance_id
            
            # Verify instance exists and is running
            print(f"Checking instance {instance_id}...")
            info = manager.get_instance_info(instance_id)
            
            if info.get('status') != 'RUNNING':
                print("Instance is not running. Please start it first.")
                sys.exit(1)
            
            # Install cloudflared if requested
            if args.install_cloudflared:
                print("Installing cloudflared...")
                
                # Upload scripts if not present
                scripts_dir = Path(__file__).parent.parent / "remote_scripts"
                manager.sync_file(instance_id, 
                                str(scripts_dir / "install_cloudflared.sh"),
                                "/home/ubuntu/remote_scripts/install_cloudflared.sh",
                                direction="upload")
                
                # Make executable and run
                ssh = manager.connect_ssh(instance_id)
                ssh.exec_command("chmod +x /home/ubuntu/remote_scripts/install_cloudflared.sh")
                
                manager.start_tmux_session(instance_id, "cloudflared-install")
                manager.run_script_in_tmux(
                    instance_id,
                    "cloudflared-install", 
                    "/home/ubuntu/remote_scripts/install_cloudflared.sh",
                    wait_for_completion=True,
                    wait_timeout=300
                )
                print("Cloudflared installation complete")
            
            # Check if tunnel session already exists
            ssh = manager.connect_ssh(instance_id)
            exit_code, _, _ = ssh.exec_command(f"tmux has-session -t {args.session_name}")
            
            if exit_code == 0:
                print(f"Tunnel session '{args.session_name}' already exists")
                print("Getting existing tunnel information...")
            else:
                # Upload tunnel script
                scripts_dir = Path(__file__).parent.parent / "remote_scripts"
                manager.sync_file(instance_id,
                                str(scripts_dir / "start_tunnel_background.sh"),
                                "/home/ubuntu/remote_scripts/start_tunnel_background.sh",
                                direction="upload")
                
                ssh.exec_command("chmod +x /home/ubuntu/remote_scripts/start_tunnel_background.sh")
                
                # Start tunnel
                print(f"Starting Cloudflare tunnel on port {args.port}...")
                exit_code, out, err = ssh.exec_command(
                    f"/home/ubuntu/remote_scripts/start_tunnel_background.sh {args.port} {args.session_name}"
                )
                
                if exit_code != 0:
                    print(f"Failed to start tunnel: {err}")
                    sys.exit(1)
                
                print(f"Tunnel started in tmux session '{args.session_name}'")
            
            # Wait for tunnel URL if requested
            if args.wait_for_url:
                print("Waiting for tunnel URL...")
                url = None
                
                for attempt in range(10):  # Try for 30 seconds
                    time.sleep(3)
                    output = manager.get_tmux_output(instance_id, args.session_name)
                    
                    if args.verbose:
                        print(f"Tunnel output (attempt {attempt + 1}):")
                        print(output)
                        print("-" * 40)
                    
                    url = extract_tunnel_url(output)
                    if url:
                        break
                
                if url:
                    print(f"\n🌐 Tunnel URL: {url}")
                    print(f"   Forwarding to: http://localhost:{args.port}")
                else:
                    print("Could not extract tunnel URL. Check tmux session manually:")
                    print(f"   tmux attach -t {args.session_name}")
            else:
                print(f"\nTunnel management commands:")
                print(f"  View tunnel: tmux attach -t {args.session_name}")
                print(f"  Kill tunnel: tmux kill-session -t {args.session_name}")
                print(f"  Get output:  tmux capture-pane -t {args.session_name} -p")
                
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
#!/usr/bin/env python3

import argparse
import sys
import time
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))
from thunder_compute_manager import ThunderComputeManager


def main():
    parser = argparse.ArgumentParser(description="Start Cloudflare tunnel and ComfyUI on Thunder instance")
    parser.add_argument("-i", "--instance-id", type=int, required=True, help="Thunder instance ID")
    parser.add_argument("-p", "--port", type=int, default=8188, help="Port for tunnel and ComfyUI (default: 8188)")
    parser.add_argument("--tunnel-session", default="tunnel", help="Tmux session name for tunnel (default: tunnel)")
    parser.add_argument("--comfy-session", default="comfyui", help="Tmux session name for ComfyUI (default: comfyui)")
    parser.add_argument("--output-dir", default="./outputs", help="Directory to save tunnel output (default: ./outputs)")
    parser.add_argument("--wait-for-url", action="store_true", help="Wait for tunnel URL to appear in output")
    parser.add_argument("--install-cloudflared", action="store_true", help="Install cloudflared if not present")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)
    
    # Generate output filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"tunnel_output_instance_{args.instance_id}_{timestamp}.txt"
    
    with ThunderComputeManager.from_secrets() as manager:
        if args.verbose:
            print(f"Starting tunnel and ComfyUI on instance {args.instance_id}")
        
        # Ensure instance is running
        instance_info = manager.get_instance_info(args.instance_id)
        if instance_info["status"] != "RUNNING":
            print(f"Instance {args.instance_id} is not running. Starting...")
            manager.start_instance(args.instance_id)
            manager.wait_for_status(args.instance_id, "RUNNING")
            print("Instance is now running")
        
        # Install cloudflared if requested
        if args.install_cloudflared:
            if args.verbose:
                print("Installing cloudflared...")
            manager.run_script_in_tmux(
                args.instance_id, 
                "install_cloudflared", 
                "/home/ubuntu/remote_scripts/install_cloudflared.sh",
                wait_for_completion=True,
                wait_timeout=300
            )
        
        # Start Cloudflare tunnel in tmux
        if args.verbose:
            print(f"Starting Cloudflare tunnel on port {args.port} in tmux session '{args.tunnel_session}'")
        
        tunnel_command = f"cd /home/ubuntu && cloudflared tunnel --url localhost:{args.port}"
        manager.start_tmux_session(args.instance_id, args.tunnel_session)
        
        # Send command to tmux session using SSH connection
        ssh = manager.connect_ssh(args.instance_id)
        manager._run_ssh_command(ssh, f"tmux send-keys -t {args.tunnel_session} '{tunnel_command}' Enter")
        
        # Wait a moment for tunnel to start
        time.sleep(5)
        
        # Start ComfyUI in separate tmux session
        if args.verbose:
            print(f"Starting ComfyUI in tmux session '{args.comfy_session}'")
        
        comfy_command = f"cd /home/ubuntu/comfy/ComfyUI && conda activate comfy-env && python main.py --listen 0.0.0.0 --port {args.port}"
        manager.start_tmux_session(args.instance_id, args.comfy_session)
        
        # Send command to tmux session using SSH connection
        manager._run_ssh_command(ssh, f"tmux send-keys -t {args.comfy_session} '{comfy_command}' Enter")
        
        # Capture tunnel output and save to file
        if args.verbose:
            print(f"Capturing tunnel output to {output_file}")
        
        tunnel_url = None
        comfy_ready = False
        start_time = time.time()
        max_wait_time = 60 if args.wait_for_url else 10
        
        with open(output_file, 'w') as f:
            f.write(f"Tunnel output for instance {args.instance_id} started at {datetime.now()}\n")
            f.write(f"Port: {args.port}\n")
            f.write("=" * 50 + "\n\n")
            
            while time.time() - start_time < max_wait_time:
                try:
                    # Check tunnel output
                    tunnel_output = manager.get_tmux_output(args.instance_id, args.tunnel_session)
                    if tunnel_output:
                        f.write("=== TUNNEL OUTPUT ===\n")
                        f.write(tunnel_output)
                        f.write("\n")
                        f.flush()
                        
                        # Look for tunnel URL in the specific format
                        if args.wait_for_url and not tunnel_url:
                            lines = tunnel_output.split('\n')
                            for line in lines:
                                # Look for the specific URL line format
                                if 'https://' in line and 'trycloudflare.com' in line and '|' in line:
                                    # Extract URL from the boxed message
                                    url_start = line.find('https://')
                                    if url_start != -1:
                                        url_end = line.find(' ', url_start)
                                        if url_end == -1:
                                            url_end = line.find('|', url_start)
                                        if url_end == -1:
                                            url_end = len(line)
                                        tunnel_url = line[url_start:url_end].strip()
                                        print(f"\n🌐 Tunnel URL found: {tunnel_url}")
                                        break
                    
                    # Check ComfyUI output
                    comfy_output = manager.get_tmux_output(args.instance_id, args.comfy_session)
                    if comfy_output:
                        f.write("=== COMFYUI OUTPUT ===\n")
                        f.write(comfy_output)
                        f.write("\n")
                        f.flush()
                        
                        # Check if ComfyUI is ready
                        if not comfy_ready and "To see the GUI go to: http://0.0.0.0:8188" in comfy_output:
                            comfy_ready = True
                            print(f"\n🎨 ComfyUI is ready to serve!")
                    
                    # Break if we have everything we need
                    if (not args.wait_for_url or tunnel_url) and comfy_ready:
                        break
                            
                except Exception as e:
                    if args.verbose:
                        print(f"Error getting output: {e}")
                
                time.sleep(2)
        
        print(f"\n✅ Setup complete!")
        print(f"📁 Tunnel output saved to: {output_file}")
        print(f"🔧 Tunnel session: {args.tunnel_session}")
        print(f"🎨 ComfyUI session: {args.comfy_session}")
        
        if tunnel_url:
            print(f"🌐 Tunnel URL: {tunnel_url}")
            if comfy_ready:
                print(f"🎨 ComfyUI is accessible at: {tunnel_url}")
            else:
                print("⏳ Waiting for ComfyUI to finish loading...")
        elif args.wait_for_url:
            print("⚠️  Tunnel URL not found in output within timeout period")
            print(f"   Check tunnel output file: {output_file}")
        
        if comfy_ready and not tunnel_url:
            print(f"🎨 ComfyUI is ready locally at: http://0.0.0.0:{args.port}")
        elif not comfy_ready:
            print("⏳ ComfyUI may still be loading - check the ComfyUI session for 'To see the GUI go to' message")
        
        print(f"\nTo monitor sessions:")
        print(f"  Tunnel: tmux attach-session -t {args.tunnel_session}")
        print(f"  ComfyUI: tmux attach-session -t {args.comfy_session}")
        print(f"\nTo get more tunnel output:")
        print(f"  python -c \"from thunder_compute_manager import ThunderComputeManager; manager = ThunderComputeManager.from_secrets(); print(manager.get_tmux_output({args.instance_id}, '{args.tunnel_session}'))\"")


if __name__ == "__main__":
    main()
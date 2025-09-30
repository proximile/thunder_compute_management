#!/usr/bin/env python3
"""
List all ThunderCompute instances with detailed information.
"""

import argparse
import json
import sys
from pathlib import Path

# Add parent directory to path for thunder_compute_manager import
sys.path.insert(0, str(Path(__file__).parent.parent))
from thunder_compute_manager import ThunderComputeManager

def format_instance_info(instance_id, info):
    """Format instance information for display."""
    status = info.get('status', 'UNKNOWN')
    ip = info.get('ip', 'N/A')
    cpu_cores = info.get('cpu_cores', 'N/A')
    gpu_type = info.get('gpu_type', 'None')
    num_gpus = info.get('num_gpus', 0)
    disk_size = info.get('disk_size_gb', 'N/A')
    
    gpu_info = f"{num_gpus}x {gpu_type}" if gpu_type and gpu_type != 'None' else "CPU only"
    
    return f"Instance {instance_id}: {status} | IP: {ip} | {cpu_cores} cores | {gpu_info} | {disk_size}GB disk"

def main():
    parser = argparse.ArgumentParser(description="List ThunderCompute instances")
    parser.add_argument("-v", "--verbose", action="store_true",
                      help="Show detailed JSON output")
    parser.add_argument("--status", choices=["RUNNING", "STOPPED", "PENDING", "ERROR"],
                      help="Filter by status")
    parser.add_argument("--json", action="store_true",
                      help="Output raw JSON")
    args = parser.parse_args()
    
    try:
        with ThunderComputeManager.from_secrets() as manager:
            print("Fetching instance list...")
            instances = manager.list_instances(force_refresh=True)
            
            if not instances:
                print("No instances found.")
                return
            
            # Filter by status if specified
            if args.status:
                instances = {k: v for k, v in instances.items() 
                           if v.get('status') == args.status}
                if not instances:
                    print(f"No instances found with status: {args.status}")
                    return
            
            print(f"\nFound {len(instances)} instance(s):")
            print("-" * 80)
            
            if args.json:
                print(json.dumps(instances, indent=2))
            else:
                for instance_id, info in instances.items():
                    print(format_instance_info(instance_id, info))
                    
                    if args.verbose:
                        print(f"  Full details: {json.dumps(info, indent=4)}")
                        print()
                        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
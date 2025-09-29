import requests
import json
import os
import time
from pathlib import Path
from typing import Optional, Tuple, Dict, Any
import paramiko


class ThunderComputeManager:
    """Manages ThunderCompute instances with SSH and tmux capabilities"""
    
    def __init__(self, api_key_path: str = "api_key.txt", 
                 ssh_key_path: str = "./rsa_key_1",
                 username: str = "ubuntu",
                 port: int = 22):
        """
        Initialize the ThunderCompute manager
        
        Args:
            api_key_path: Path to API key file
            ssh_key_path: Path to SSH private key
            username: SSH username (default: ubuntu)
            port: SSH port (default: 22)
        """
        self.api_base_url = "https://api.thundercompute.com:8443"
        self.token = self._load_api_key(api_key_path)
        self.headers = {"Authorization": f"Bearer {self.token}"}
        self.ssh_key_path = Path(ssh_key_path).expanduser().resolve()
        self.username = username
        self.port = port
        self._ssh_connections = {}  # Cache SSH connections
        self._instances_cache = None
        self._cache_time = 0
        self._cache_ttl = 30  # Cache TTL in seconds
        
    def _load_api_key(self, path: str) -> str:
        """Load API key from file"""
        with open(path, "r") as f:
            return f.read().strip()
    
    def list_instances(self, force_refresh: bool = False) -> Dict[str, Any]:
        """
        List all instances with caching
        
        Args:
            force_refresh: Force refresh the cache
            
        Returns:
            Dictionary of instances
        """
        if not force_refresh and self._instances_cache and \
           (time.time() - self._cache_time) < self._cache_ttl:
            return self._instances_cache
            
        url = f"{self.api_base_url}/instances/list"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        self._instances_cache = response.json()
        self._cache_time = time.time()
        return self._instances_cache
    
    def get_instance_info(self, instance_id: int) -> Dict[str, Any]:
        """Get information about a specific instance"""
        instances = self.list_instances()
        instance_id_str = str(instance_id)
        if instance_id_str not in instances:
            raise ValueError(f"Instance {instance_id} not found")
        return instances[instance_id_str]
    
    def get_ip(self, instance_id: int) -> Optional[str]:
        """Get IP address of an instance"""
        return self.get_instance_info(instance_id).get("ip")
    
    def start_instance(self, instance_id: int) -> requests.Response:
        """Start an instance"""
        url = f"{self.api_base_url}/instances/{instance_id}/up"
        response = requests.post(url, headers=self.headers)
        response.raise_for_status()
        self._instances_cache = None  # Invalidate cache
        return response
    
    def stop_instance(self, instance_id: int) -> requests.Response:
        """Stop an instance"""
        url = f"{self.api_base_url}/instances/{instance_id}/down"
        response = requests.post(url, headers=self.headers)
        response.raise_for_status()
        self._instances_cache = None  # Invalidate cache
        return response
    
    def wait_for_status(self, instance_id: int, status: str = "RUNNING", 
                       timeout: int = 60) -> bool:
        """
        Wait for instance to reach desired status
        
        Args:
            instance_id: Instance ID
            status: Desired status
            timeout: Maximum wait time in seconds
            
        Returns:
            True if status reached, False if timeout
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            current_status = self.get_instance_info(instance_id)["status"]
            if current_status == status:
                return True
            time.sleep(1)
            self.list_instances(force_refresh=True)  # Refresh cache
        return False
    
    def connect_ssh(self, instance_id: int, timeout: float = 15.0) -> paramiko.SSHClient:
        """
        Connect to instance via SSH (with connection caching)
        
        Args:
            instance_id: Instance ID
            timeout: Connection timeout
            
        Returns:
            Connected SSH client
        """
        # Check if we have a cached connection
        if instance_id in self._ssh_connections:
            ssh = self._ssh_connections[instance_id]
            # Test if connection is still alive
            try:
                ssh.exec_command("echo test", timeout=1)
                return ssh
            except:
                # Connection is dead, remove from cache
                del self._ssh_connections[instance_id]
        
        # Get IP address
        ip = self.get_ip(instance_id)
        if not ip:
            raise ValueError(f"Instance {instance_id} has no IP address (not running?)")
        
        # Verify SSH key exists
        if not self.ssh_key_path.exists():
            raise FileNotFoundError(f"SSH key not found at: {self.ssh_key_path}")
        
        # Load SSH key
        pkey = self._load_ssh_key()
        
        # Create SSH connection
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(
            hostname=ip,
            username=self.username,
            port=self.port,
            pkey=pkey,
            look_for_keys=False,
            allow_agent=False,
            timeout=timeout,
            banner_timeout=timeout,
            auth_timeout=timeout,
        )
        
        # Cache the connection
        self._ssh_connections[instance_id] = ssh
        return ssh
    
    def _load_ssh_key(self) -> paramiko.PKey:
        """Load SSH private key"""
        load_errors = []
        for loader in (paramiko.RSAKey, paramiko.ECDSAKey, paramiko.Ed25519Key):
            try:
                return loader.from_private_key_file(str(self.ssh_key_path))
            except Exception as e:
                load_errors.append(e)
        raise ValueError(f"Failed to load key {self.ssh_key_path}: {load_errors[-1]}")
    
    def _run_ssh_command(self, ssh: paramiko.SSHClient, cmd: str, 
                        timeout: Optional[float] = 30.0) -> Tuple[int, str, str]:
        """Run a command over SSH"""
        stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
        out = stdout.read().decode("utf-8", errors="replace")
        err = stderr.read().decode("utf-8", errors="replace")
        exit_status = stdout.channel.recv_exit_status()
        return exit_status, out, err
    
    def start_tmux_session(self, instance_id: int, session_name: str,
                          cwd: Optional[str] = None, 
                          history_limit: int = 100000) -> bool:
        """
        Start a tmux session on the instance
        
        Args:
            instance_id: Instance ID
            session_name: Name for the tmux session
            cwd: Working directory for the session
            history_limit: Tmux history limit
            
        Returns:
            True if new session created, False if already existed
        """
        ssh = self.connect_ssh(instance_id)
        
        # Check if session exists
        rc, _, _ = self._run_ssh_command(ssh, f'tmux has-session -t {session_name} 2>/dev/null')
        if rc == 0:
            # Session exists, update history limit
            self._run_ssh_command(ssh, f'tmux set-option -t {session_name} history-limit {history_limit} >/dev/null 2>&1')
            return False
        
        # Create new session
        pre = f'cd {cwd} && ' if cwd else ''
        rc, out, err = self._run_ssh_command(ssh, f'{pre}tmux new-session -d -s {session_name}')
        if rc != 0:
            raise RuntimeError(f"Failed to start tmux session '{session_name}': {err or out}")
        
        # Set history limit
        self._run_ssh_command(ssh, f'tmux set-option -t {session_name} history-limit {history_limit} >/dev/null 2>&1')
        return True
    
    def run_script_in_tmux(self, instance_id: int, session_name: str,
                          script_path: str, initialize_if_missing: bool = True,
                          cwd: Optional[str] = None, env: Optional[Dict[str, str]] = None,
                          wait_for_completion: bool = False, wait_timeout: float = 120.0) -> None:
        """
        Run a script in a tmux session
        
        Args:
            instance_id: Instance ID
            session_name: Tmux session name
            script_path: Path to script on remote host
            initialize_if_missing: Create session if it doesn't exist
            cwd: Working directory
            env: Environment variables
            wait_for_completion: Wait for script to complete
            wait_timeout: Maximum wait time if waiting
        """
        ssh = self.connect_ssh(instance_id)
        
        # Ensure session exists
        rc, _, _ = self._run_ssh_command(ssh, f'tmux has-session -t {session_name} 2>/dev/null')
        if rc != 0:
            if not initialize_if_missing:
                raise RuntimeError(f"tmux session '{session_name}' does not exist")
            self.start_tmux_session(instance_id, session_name, cwd=cwd)
        
        # Build command
        cd_prefix = f'cd {cwd} && ' if cwd else ''
        env_prefix = ""
        if env:
            parts = []
            for k, v in env.items():
                k = str(k).replace('"', '\\"')
                v = str(v).replace('"', '\\"')
                parts.append(f'{k}="{v}"')
            env_prefix = " ".join(parts) + " "
        
        if wait_for_completion:
            # Add sentinel for completion detection
            sentinel = "__TMUX_CMD_DONE__"
            bash_cmd = f'{cd_prefix}{env_prefix}bash "{script_path}" ; ec=$?; echo {sentinel}$ec'
            send = f'tmux send-keys -t {session_name} {bash_cmd!r} C-m'
            self._run_ssh_command(ssh, send)
            
            # Poll for completion
            deadline = time.time() + wait_timeout
            while time.time() < deadline:
                rc, out, _ = self._run_ssh_command(ssh, f'tmux capture-pane -p -J -S - -t {session_name}')
                if sentinel in out:
                    break
                time.sleep(1.0)
        else:
            bash_cmd = f'{cd_prefix}{env_prefix}bash "{script_path}"'
            send = f'tmux send-keys -t {session_name} {bash_cmd!r} C-m'
            self._run_ssh_command(ssh, send)
    
    def get_tmux_output(self, instance_id: int, session_name: str, 
                       compress_join_wrapped: bool = True) -> str:
        """
        Get output from a tmux session
        
        Args:
            instance_id: Instance ID
            session_name: Tmux session name
            compress_join_wrapped: Join wrapped lines
            
        Returns:
            Tmux pane output as string
        """
        ssh = self.connect_ssh(instance_id)
        join_flag = "-J " if compress_join_wrapped else ""
        rc, out, err = self._run_ssh_command(ssh, f'tmux capture-pane -p {join_flag}-S - -t {session_name}')
        if rc != 0:
            raise RuntimeError(f"Failed to capture tmux output for '{session_name}': {err or out}")
        return out
    
    def close_ssh(self, instance_id: Optional[int] = None):
        """
        Close SSH connection(s)
        
        Args:
            instance_id: Close specific connection, or None to close all
        """
        if instance_id is not None:
            if instance_id in self._ssh_connections:
                try:
                    self._ssh_connections[instance_id].close()
                except:
                    pass
                del self._ssh_connections[instance_id]
        else:
            # Close all connections
            for ssh in self._ssh_connections.values():
                try:
                    ssh.close()
                except:
                    pass
            self._ssh_connections.clear()
    
    def __del__(self):
        """Cleanup SSH connections on deletion"""
        self.close_ssh()
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - close all SSH connections"""
        self.close_ssh()

import requests
import json
import os
import time
from pathlib import Path
from typing import Optional, Tuple, Dict, Any
import paramiko
import re
import shutil
import subprocess
import stat

class ThunderComputeManager:
    """Manages ThunderCompute instances with SSH and tmux capabilities"""
    
    def __init__(self, api_key_path: str = "./secrets/api_key.txt", 
                secrets_dir: str = "./secrets",
                username: str = "ubuntu",
                port: int = 22,
                auto_setup_keys: bool = True):
        """
        Initialize the ThunderCompute manager
        
        Args:
            api_key_path: Path to API key file (default: ./secrets/api_key.txt)
            secrets_dir: Directory for storing SSH keys and API key
            username: SSH username (default: ubuntu)
            port: SSH port (default: 22)
            auto_setup_keys: Automatically setup SSH keys when connecting to instances
        """
        self.api_base_url = "https://api.thundercompute.com:8443"
        
        # Ensure secrets directory exists before loading API key
        self.secrets_dir = Path(secrets_dir).resolve()
        self.secrets_dir.mkdir(parents=True, exist_ok=True)
        
        # Load API key with proper path handling
        self.token = self._load_api_key(api_key_path)
        self.headers = {"Authorization": f"Bearer {self.token}"}
        self.username = username
        self.port = port
        self.auto_setup_keys = auto_setup_keys
        self._ssh_connections = {}
        self._instance_keys = {}  # Maps instance_id -> ssh_key_path
        self._instances_cache = None
        self._cache_time = 0
        self._cache_ttl = 30
        
    def _load_api_key(self, path: str) -> str:
        """
        Load API key from file
        
        Args:
            path: Path to API key file (can be relative or absolute)
            
        Returns:
            API key string
            
        Raises:
            FileNotFoundError: If API key file doesn't exist
            ValueError: If API key file is empty
        """
        # Handle path resolution
        api_key_path = Path(path).expanduser().resolve()
        
        # If the path doesn't exist and it's just a filename, try the secrets directory
        if not api_key_path.exists() and not os.path.dirname(path):
            api_key_path = self.secrets_dir / path
        
        if not api_key_path.exists():
            raise FileNotFoundError(
                f"API key file not found at: {api_key_path}\n"
                f"Please ensure the API key is saved in {api_key_path}"
            )
        
        try:
            with open(api_key_path, "r") as f:
                api_key = f.read().strip()
        except PermissionError:
            raise PermissionError(f"Permission denied reading API key from: {api_key_path}")
        except Exception as e:
            raise RuntimeError(f"Error reading API key from {api_key_path}: {e}")
        
        if not api_key:
            raise ValueError(f"API key file is empty: {api_key_path}")
        
        print(f"API key loaded from: {api_key_path}")
        return api_key
    
    @classmethod
    def from_secrets(cls, secrets_dir: str = "./secrets",
                    auto_setup_keys: bool = True,
                    **kwargs):
        """
        Convenience factory method to create manager with secrets directory defaults
        
        Args:
            secrets_dir: Directory containing api_key.txt and SSH keys
            auto_setup_keys: Automatically setup SSH keys when needed
            **kwargs: Additional arguments to pass to __init__
            
        Returns:
            Configured ThunderComputeManager instance
            
        Example:
            # Create manager that will auto-setup keys as needed
            manager = ThunderComputeManager.from_secrets()
            
            # Then connect to any instance - keys will be handled automatically
            ssh = manager.connect_ssh(12345)
        """
        api_key_path = str(Path(secrets_dir) / "api_key.txt")
        
        return cls(
            api_key_path=api_key_path,
            secrets_dir=secrets_dir,
            auto_setup_keys=auto_setup_keys,
            **kwargs
        )

    def validate_secrets_setup(self, instance_ids: Optional[list[int]] = None) -> Dict[str, Any]:
        """
        Validate that secrets are properly configured
        
        Args:
            instance_ids: Optional list of instance IDs to check SSH keys for
        
        Returns:
            Dictionary with validation results:
            - api_key_valid: Whether API key is loaded
            - secrets_dir: Path to secrets directory
            - instance_keys: Status of SSH keys for each instance
            - can_connect: Whether API connection works
        """
        results = {
            'secrets_dir': str(self.secrets_dir),
            'api_key_valid': bool(self.token),
            'can_connect': False,
            'instance_keys': {}
        }
        
        # Test API connection
        try:
            instances = self.list_instances()
            results['can_connect'] = True
            results['instance_count'] = len(instances)
            
            # If no instance_ids specified, check all available instances
            if instance_ids is None and instances:
                instance_ids = [int(iid) for iid in instances.keys()]
        except Exception as e:
            results['connection_error'] = str(e)
        
        # Check SSH keys for specified instances
        if instance_ids:
            for instance_id in instance_ids:
                key_info = {
                    'instance_id': instance_id,
                    'key_exists': False,
                    'key_path': None,
                    'permissions_ok': False
                }
                
                try:
                    key_path = self.secrets_dir / f"id_rsa_instance_{instance_id}"
                    key_info['key_path'] = str(key_path)
                    
                    if key_path.exists():
                        key_info['key_exists'] = True
                        mode = oct(key_path.stat().st_mode)[-3:]
                        key_info['permissions'] = mode
                        key_info['permissions_ok'] = mode in ('600', '400')
                    else:
                        key_info['ssh_config_exists'] = self.get_ssh_config_info(instance_id) is not None
                        
                except Exception as e:
                    key_info['error'] = str(e)
                
                results['instance_keys'][instance_id] = key_info
        
        return results
    
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
        
        # Get or setup SSH key for this specific instance
        if instance_id not in self._instance_keys:
            if self.auto_setup_keys:
                # Auto-setup key for this instance
                key_path = self.ensure_rsa_key(instance_id, str(self.secrets_dir))
                self._instance_keys[instance_id] = key_path
            else:
                # Try to find existing key
                key_path = self.secrets_dir / f"id_rsa_instance_{instance_id}"
                if key_path.exists():
                    self._instance_keys[instance_id] = str(key_path)
                else:
                    raise FileNotFoundError(
                        f"SSH key not found for instance {instance_id} at: {key_path}\n"
                        f"Run 'manager.ensure_rsa_key({instance_id})' to set it up."
                    )
        
        ssh_key_path = Path(self._instance_keys[instance_id])
        
        # Verify SSH key exists
        if not ssh_key_path.exists():
            raise FileNotFoundError(f"SSH key not found at: {ssh_key_path}")
        
        # Load SSH key
        pkey = self._load_ssh_key_from_path(ssh_key_path)
        
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
        """Load SSH private key (deprecated - use _load_ssh_key_from_path)"""
        # This method is kept for backward compatibility
        if hasattr(self, 'ssh_key_path'):
            return self._load_ssh_key_from_path(self.ssh_key_path)
        else:
            raise RuntimeError("No default SSH key path configured")
    
    def _load_ssh_key_from_path(self, key_path: Path) -> paramiko.PKey:
        """Load SSH private key from specific path"""
        load_errors = []
        for loader in (paramiko.RSAKey, paramiko.ECDSAKey, paramiko.Ed25519Key):
            try:
                return loader.from_private_key_file(str(key_path))
            except Exception as e:
                load_errors.append(e)
        raise ValueError(f"Failed to load key {key_path}: {load_errors[-1]}")
    
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

    def upload_file(self, instance_id: int, local_path: str, remote_path: str,
                    create_dirs: bool = True) -> None:
        """
        Upload a file from local to remote instance
        
        Args:
            instance_id: Instance ID
            local_path: Local file path
            remote_path: Remote destination path
            create_dirs: Create parent directories if they don't exist
        
        Raises:
            FileNotFoundError: If local file doesn't exist
            RuntimeError: If upload fails
        """
        local_path = Path(local_path).expanduser().resolve()
        if not local_path.exists():
            raise FileNotFoundError(f"Local file not found: {local_path}")
        
        ssh = self.connect_ssh(instance_id)
        
        try:
            sftp = ssh.open_sftp()
            
            # Create parent directories if needed
            if create_dirs:
                remote_dir = str(Path(remote_path).parent)
                try:
                    sftp.stat(remote_dir)
                except FileNotFoundError:
                    # Create directories recursively
                    dirs_to_create = []
                    current = remote_dir
                    while current and current != '/':
                        try:
                            sftp.stat(current)
                            break
                        except FileNotFoundError:
                            dirs_to_create.append(current)
                            current = str(Path(current).parent)
                    
                    # Create dirs from parent to child
                    for dir_path in reversed(dirs_to_create):
                        sftp.mkdir(dir_path)
            
            # Upload the file
            sftp.put(str(local_path), remote_path)
            
            # Preserve file permissions if possible
            local_stat = local_path.stat()
            sftp.chmod(remote_path, stat.S_IMODE(local_stat.st_mode))
            
            sftp.close()
            
        except Exception as e:
            raise RuntimeError(f"Failed to upload {local_path} to {remote_path}: {e}")

    def download_file(self, instance_id: int, remote_path: str, local_path: str,
                    create_dirs: bool = True) -> None:
        """
        Download a file from remote instance to local
        
        Args:
            instance_id: Instance ID
            remote_path: Remote file path
            local_path: Local destination path
            create_dirs: Create parent directories if they don't exist
        
        Raises:
            FileNotFoundError: If remote file doesn't exist
            RuntimeError: If download fails
        """
        local_path = Path(local_path).expanduser().resolve()
        
        # Create local parent directories if needed
        if create_dirs:
            local_path.parent.mkdir(parents=True, exist_ok=True)
        
        ssh = self.connect_ssh(instance_id)
        
        try:
            sftp = ssh.open_sftp()
            
            # Check if remote file exists
            try:
                sftp.stat(remote_path)
            except FileNotFoundError:
                raise FileNotFoundError(f"Remote file not found: {remote_path}")
            
            # Download the file
            sftp.get(remote_path, str(local_path))
            
            # Try to preserve permissions
            try:
                remote_stat = sftp.stat(remote_path)
                os.chmod(local_path, stat.S_IMODE(remote_stat.st_mode))
            except:
                pass  # Permission preservation is best-effort
            
            sftp.close()
            
        except FileNotFoundError:
            raise
        except Exception as e:
            raise RuntimeError(f"Failed to download {remote_path} to {local_path}: {e}")

    def upload_directory(self, instance_id: int, local_dir: str, remote_dir: str,
                        recursive: bool = True) -> None:
        """
        Upload a directory from local to remote instance
        
        Args:
            instance_id: Instance ID
            local_dir: Local directory path
            remote_dir: Remote destination directory
            recursive: Upload subdirectories recursively
        
        Raises:
            NotADirectoryError: If local path is not a directory
            RuntimeError: If upload fails
        """
        local_dir = Path(local_dir).expanduser().resolve()
        if not local_dir.is_dir():
            raise NotADirectoryError(f"Local path is not a directory: {local_dir}")
        
        ssh = self.connect_ssh(instance_id)
        
        try:
            sftp = ssh.open_sftp()
            
            # Create remote directory if it doesn't exist
            try:
                sftp.stat(remote_dir)
            except FileNotFoundError:
                sftp.mkdir(remote_dir)
            
            # Walk through local directory
            for root, dirs, files in os.walk(local_dir):
                # Calculate relative path
                rel_path = Path(root).relative_to(local_dir)
                remote_root = str(Path(remote_dir) / rel_path)
                
                # Create directories
                for dir_name in dirs:
                    remote_subdir = str(Path(remote_root) / dir_name)
                    try:
                        sftp.stat(remote_subdir)
                    except FileNotFoundError:
                        sftp.mkdir(remote_subdir)
                
                # Upload files
                for file_name in files:
                    local_file = Path(root) / file_name
                    remote_file = str(Path(remote_root) / file_name)
                    sftp.put(str(local_file), remote_file)
                    
                    # Preserve permissions
                    try:
                        local_stat = local_file.stat()
                        sftp.chmod(remote_file, stat.S_IMODE(local_stat.st_mode))
                    except:
                        pass
                
                # If not recursive, only process the top level
                if not recursive:
                    break
            
            sftp.close()
            
        except Exception as e:
            raise RuntimeError(f"Failed to upload directory {local_dir} to {remote_dir}: {e}")

    def download_directory(self, instance_id: int, remote_dir: str, local_dir: str,
                        recursive: bool = True) -> None:
        """
        Download a directory from remote instance to local
        
        Args:
            instance_id: Instance ID
            remote_dir: Remote directory path
            local_dir: Local destination directory
            recursive: Download subdirectories recursively
        
        Raises:
            NotADirectoryError: If remote path is not a directory
            RuntimeError: If download fails
        """
        local_dir = Path(local_dir).expanduser().resolve()
        
        ssh = self.connect_ssh(instance_id)
        
        try:
            sftp = ssh.open_sftp()
            
            # Check if remote directory exists
            remote_stat = sftp.stat(remote_dir)
            if not stat.S_ISDIR(remote_stat.st_mode):
                raise NotADirectoryError(f"Remote path is not a directory: {remote_dir}")
            
            # Create local directory if it doesn't exist
            local_dir.mkdir(parents=True, exist_ok=True)
            
            def _download_dir(remote_path: str, local_path: Path):
                """Recursively download directory contents"""
                for item in sftp.listdir_attr(remote_path):
                    remote_item = f"{remote_path}/{item.filename}"
                    local_item = local_path / item.filename
                    
                    if stat.S_ISDIR(item.st_mode):
                        if recursive:
                            local_item.mkdir(exist_ok=True)
                            _download_dir(remote_item, local_item)
                    else:
                        # Download file
                        sftp.get(remote_item, str(local_item))
                        # Preserve permissions
                        try:
                            os.chmod(local_item, stat.S_IMODE(item.st_mode))
                        except:
                            pass
            
            _download_dir(remote_dir, local_dir)
            sftp.close()
            
        except Exception as e:
            raise RuntimeError(f"Failed to download directory {remote_dir} to {local_dir}: {e}")

    def sync_file(self, instance_id: int, local_path: str, remote_path: str,
                direction: str = "upload", overwrite_newer: bool = False) -> bool:
        """
        Sync a file between local and remote, only transferring if needed
        
        Args:
            instance_id: Instance ID
            local_path: Local file path
            remote_path: Remote file path
            direction: "upload" or "download"
            overwrite_newer: Overwrite even if destination is newer
        
        Returns:
            True if file was transferred, False if skipped
            
        Raises:
            ValueError: If direction is invalid
            FileNotFoundError: If source file doesn't exist
        """
        if direction not in ("upload", "download"):
            raise ValueError("Direction must be 'upload' or 'download'")
        
        local_path = Path(local_path).expanduser().resolve()
        ssh = self.connect_ssh(instance_id)
        
        try:
            sftp = ssh.open_sftp()
            
            # Get file stats
            local_exists = local_path.exists()
            try:
                remote_stat = sftp.stat(remote_path)
                remote_exists = True
            except FileNotFoundError:
                remote_exists = False
                remote_stat = None
            
            if direction == "upload":
                if not local_exists:
                    raise FileNotFoundError(f"Local file not found: {local_path}")
                
                if not remote_exists:
                    # Remote doesn't exist, upload needed
                    self.upload_file(instance_id, str(local_path), remote_path)
                    return True
                
                # Both exist, compare timestamps
                local_mtime = local_path.stat().st_mtime
                remote_mtime = remote_stat.st_mtime
                
                if local_mtime > remote_mtime or overwrite_newer:
                    self.upload_file(instance_id, str(local_path), remote_path)
                    return True
                    
            else:  # download
                if not remote_exists:
                    raise FileNotFoundError(f"Remote file not found: {remote_path}")
                
                if not local_exists:
                    # Local doesn't exist, download needed
                    self.download_file(instance_id, remote_path, str(local_path))
                    return True
                
                # Both exist, compare timestamps
                local_mtime = local_path.stat().st_mtime
                remote_mtime = remote_stat.st_mtime
                
                if remote_mtime > local_mtime or overwrite_newer:
                    self.download_file(instance_id, remote_path, str(local_path))
                    return True
            
            sftp.close()
            return False
            
        except Exception as e:
            if "not found" in str(e).lower():
                raise
            raise RuntimeError(f"Failed to sync file: {e}")

    def create_instance(self, 
                    cpu_cores: int = 4,
                    template: str = "base",
                    gpu_type: Optional[str] = None,
                    num_gpus: Optional[int] = None,
                    disk_size_gb: int = 100,
                    mode: str = "production",
                    wait_for_running: bool = True,
                    wait_timeout: int = 120) -> Dict[str, Any]:
        """
        Create a new ThunderCompute instance
        
        Args:
            cpu_cores: Number of CPU cores (default: 4)
            template: Instance template to use (default: "base")
            gpu_type: Type of GPU (e.g., "t4", "a100", None for CPU-only)
            num_gpus: Number of GPUs (required if gpu_type is specified)
            disk_size_gb: Disk size in GB (default: 100)
            mode: Instance mode - "production" or "prototyping" (default: "production")
            wait_for_running: Wait for instance to be in RUNNING state
            wait_timeout: Maximum time to wait for instance to start (seconds)
        
        Returns:
            Dictionary containing:
            - uuid: Instance UUID
            - key: Instance key
            - identifier: Instance identifier
            - instance_id: Extracted instance ID (if available)
        
        Raises:
            ValueError: If GPU configuration is invalid
            RuntimeError: If instance creation fails
        """
        # Validate GPU configuration
        if gpu_type and not num_gpus:
            raise ValueError("num_gpus must be specified when gpu_type is provided")
        if num_gpus and not gpu_type:
            raise ValueError("gpu_type must be specified when num_gpus is provided")
        
        # Build payload
        payload = {
            "cpu_cores": cpu_cores,
            "template": template,
            "disk_size_gb": disk_size_gb,
            "mode": mode
        }
        
        if gpu_type:
            payload["gpu_type"] = gpu_type
            payload["num_gpus"] = num_gpus
        
        # Create instance
        url = f"{self.api_base_url}/instances/create"
        response = requests.post(url, json=payload, headers=self.headers)
        
        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            error_data = response.json() if response.content else {}
            raise RuntimeError(f"Failed to create instance: {e}\nDetails: {error_data}")
        
        result = response.json()
        
        # Invalidate cache to force refresh
        self._instances_cache = None
        
        # Extract instance ID from identifier (API returns it directly as integer)
        if 'identifier' in result:
            instance_id = result['identifier']
            result['instance_id'] = instance_id
            
            # Save SSH key to secrets directory if provided
            if 'key' in result and result['key']:
                try:
                    key_path = self.secrets_dir / f"id_rsa_instance_{instance_id}"
                    with open(key_path, 'w') as f:
                        f.write(result['key'])
                    os.chmod(key_path, 0o600)
                    print(f"SSH key saved to {key_path}")
                    
                    # Clear cached connections and keys for this instance ID
                    if instance_id in self._ssh_connections:
                        try:
                            self._ssh_connections[instance_id].close()
                        except:
                            pass
                        del self._ssh_connections[instance_id]
                    
                    # Update instance keys cache with new key
                    self._instance_keys[instance_id] = str(key_path)
                    
                except Exception as e:
                    print(f"Warning: Failed to save SSH key: {e}")
        
        # Wait for instance to be running if requested
        if wait_for_running and 'instance_id' in result:
            print(f"Waiting for instance {result['instance_id']} to start...")
            if self.wait_for_status(result['instance_id'], "RUNNING", timeout=wait_timeout):
                print(f"Instance {result['instance_id']} is now running")
                # Get and add IP to result
                result['ip'] = self.get_ip(result['instance_id'])
            else:
                print(f"Warning: Instance {result['instance_id']} did not reach RUNNING state within {wait_timeout}s")
        
        return result

    def delete_instance(self, instance_id: int, confirm: bool = False) -> Dict[str, Any]:
        """
        Delete a ThunderCompute instance
        
        Args:
            instance_id: Instance ID to delete
            confirm: Safety flag - must be True to actually delete
        
        Returns:
            API response dictionary containing:
            - code: Response code
            - status: Status string
            - message: Response message
            - errors: Any error details
        
        Raises:
            ValueError: If confirm is not True
            RuntimeError: If deletion fails
        """
        if not confirm:
            raise ValueError("Must set confirm=True to delete an instance. This action cannot be undone!")
        
        # Check if instance exists
        try:
            instance_info = self.get_instance_info(instance_id)
            print(f"Deleting instance {instance_id} (Status: {instance_info.get('status')})")
        except ValueError:
            raise ValueError(f"Instance {instance_id} not found")
        
        # Close any SSH connections to this instance
        self.close_ssh(instance_id)
        
        # Delete the instance
        url = f"{self.api_base_url}/instances/{instance_id}/delete"
        response = requests.post(url, headers=self.headers)
        
        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            error_data = response.json() if response.content else {}
            raise RuntimeError(f"Failed to delete instance {instance_id}: {e}\nDetails: {error_data}")
        
        result = response.json()
        
        # Invalidate cache
        self._instances_cache = None
        
        print(f"Instance {instance_id} deleted successfully")
        return result

    def modify_instance(self, instance_id: int,
                    cpu_cores: Optional[int] = None,
                    gpu_type: Optional[str] = None,
                    num_gpus: Optional[int] = None,
                    disk_size_gb: Optional[int] = None,
                    stop_before_modify: bool = True,
                    restart_after_modify: bool = True,
                    wait_timeout: int = 60) -> Dict[str, Any]:
        """
        Modify configuration of an existing instance
        
        Note: Instance typically needs to be stopped to modify configuration
        
        Args:
            instance_id: Instance ID to modify
            cpu_cores: New CPU core count (None to keep current)
            gpu_type: New GPU type (None to keep current, "none" to remove GPUs)
            num_gpus: New GPU count (None to keep current, 0 to remove GPUs)
            disk_size_gb: New disk size in GB (None to keep current, must be >= current size)
            stop_before_modify: Automatically stop instance before modification
            restart_after_modify: Automatically restart instance after modification
            wait_timeout: Maximum time to wait for state changes (seconds)
        
        Returns:
            API response dictionary
        
        Raises:
            RuntimeError: If modification fails
        """
        # Get current instance state
        current_info = self.get_instance_info(instance_id)
        was_running = current_info.get('status') == 'RUNNING'
        
        # Stop instance if needed
        if stop_before_modify and was_running:
            print(f"Stopping instance {instance_id} for modification...")
            self.stop_instance(instance_id)
            if not self.wait_for_status(instance_id, "STOPPED", timeout=wait_timeout):
                raise RuntimeError(f"Failed to stop instance {instance_id} within {wait_timeout}s")
        
        # Build modification payload
        payload = {}
        if cpu_cores is not None:
            payload["cpu_cores"] = cpu_cores
        
        # Handle GPU modifications
        if gpu_type is not None:
            if gpu_type.lower() == "none":
                # Remove GPUs
                payload["num_gpus"] = 0
            else:
                payload["gpu_type"] = gpu_type
                if num_gpus is not None:
                    payload["num_gpus"] = num_gpus
        elif num_gpus is not None:
            payload["num_gpus"] = num_gpus
        
        if disk_size_gb is not None:
            # Validate disk size (can only increase)
            current_disk = current_info.get('disk_size_gb', 0)
            if disk_size_gb < current_disk:
                raise ValueError(f"Cannot reduce disk size from {current_disk}GB to {disk_size_gb}GB")
            payload["disk_size_gb"] = disk_size_gb
        
        if not payload:
            print("No modifications specified")
            return {"message": "No changes made"}
        
        # Modify the instance
        url = f"{self.api_base_url}/instances/{instance_id}/modify"
        response = requests.post(url, json=payload, headers=self.headers)
        
        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            error_data = response.json() if response.content else {}
            raise RuntimeError(f"Failed to modify instance {instance_id}: {e}\nDetails: {error_data}")
        
        result = response.json()
        
        # Invalidate cache
        self._instances_cache = None
        
        print(f"Instance {instance_id} modified successfully")
        
        # Restart if requested and was running
        if restart_after_modify and was_running:
            print(f"Restarting instance {instance_id}...")
            self.start_instance(instance_id)
            if self.wait_for_status(instance_id, "RUNNING", timeout=wait_timeout):
                print(f"Instance {instance_id} is running again")
            else:
                print(f"Warning: Instance {instance_id} did not restart within {wait_timeout}s")
        
        return result

    def clone_instance(self, source_instance_id: int,
                    new_name: Optional[str] = None,
                    cpu_cores: Optional[int] = None,
                    gpu_type: Optional[str] = None,
                    num_gpus: Optional[int] = None,
                    disk_size_gb: Optional[int] = None,
                    start_after_create: bool = True) -> Dict[str, Any]:
        """
        Clone an existing instance with optional modifications
        
        Args:
            source_instance_id: Instance ID to clone from
            new_name: Name for the new instance (optional)
            cpu_cores: Override CPU cores (None to use source config)
            gpu_type: Override GPU type (None to use source config)
            num_gpus: Override GPU count (None to use source config)
            disk_size_gb: Override disk size (None to use source config)
            start_after_create: Start the new instance after creation
        
        Returns:
            New instance information
        
        Raises:
            RuntimeError: If cloning fails
        """
        # Get source instance configuration
        source_info = self.get_instance_info(source_instance_id)
        
        # Build configuration for new instance
        config = {
            'cpu_cores': cpu_cores or source_info.get('cpu_cores', 4),
            'template': source_info.get('template', 'base'),
            'gpu_type': gpu_type or source_info.get('gpu_type'),
            'num_gpus': num_gpus if num_gpus is not None else source_info.get('num_gpus'),
            'disk_size_gb': disk_size_gb or source_info.get('disk_size_gb', 100),
            'mode': source_info.get('mode', 'production')
        }
        
        print(f"Cloning instance {source_instance_id} with config: {config}")
        
        # Create the new instance
        new_instance = self.create_instance(
            wait_for_running=start_after_create,
            **config
        )
        
        if new_name and 'instance_id' in new_instance:
            print(f"New instance created: {new_instance['instance_id']}")
            # Note: API doesn't support naming, but you could track this locally
        
        return new_instance

    def get_instance_cost_estimate(self, instance_id: int,
                                hours: float = 1.0) -> Dict[str, float]:
        """
        Estimate the cost for running an instance
        
        Args:
            instance_id: Instance ID
            hours: Number of hours to estimate for
        
        Returns:
            Dictionary with cost breakdown (estimated)
        
        Note: These are example rates - check Thunder Compute pricing for actual rates
        """
        info = self.get_instance_info(instance_id)
        
        # Example pricing (replace with actual Thunder Compute rates)
        cpu_rate = 0.01  # per core per hour
        gpu_rates = {
            't4': 0.35,
            'a100xl': 2.50,
        }
        storage_rate = 0.0001  # per GB per hour
        
        cpu_cost = info.get('cpu_cores', 0) * cpu_rate * hours
        
        gpu_cost = 0
        if info.get('gpu_type') and info.get('num_gpus'):
            gpu_type = info['gpu_type'].lower()
            gpu_cost = gpu_rates.get(gpu_type, 1.0) * info['num_gpus'] * hours
        
        storage_cost = info.get('disk_size_gb', 0) * storage_rate * hours
        
        return {
            'cpu_cost': round(cpu_cost, 4),
            'gpu_cost': round(gpu_cost, 4),
            'storage_cost': round(storage_cost, 4),
            'total_cost': round(cpu_cost + gpu_cost + storage_cost, 4),
            'hours': hours,
            'note': 'Estimated costs - check Thunder Compute for actual pricing'
        }

    def ensure_rsa_key(self, instance_id: int, 
                    secrets_dir: str = "./secrets",
                    force_refresh: bool = False) -> str:
        """
        Ensure RSA key exists in secrets directory for the given instance.
        Extracts from ~/.ssh/config if needed, runs 'tnr connect' if entry missing.
        
        Args:
            instance_id: Thunder Compute instance ID
            secrets_dir: Local directory to store RSA keys (default: ./secrets)
            force_refresh: Force re-extraction even if key exists
        
        Returns:
            Path to the RSA key file in secrets directory
        
        Raises:
            RuntimeError: If unable to obtain RSA key
        """
        # Create secrets directory if it doesn't exist
        secrets_path = Path(secrets_dir).resolve()
        secrets_path.mkdir(parents=True, exist_ok=True)
        
        # Expected key filename in secrets directory
        key_filename = f"id_rsa_instance_{instance_id}"
        local_key_path = secrets_path / key_filename
        
        # Check if key already exists in secrets
        if local_key_path.exists() and not force_refresh:
            print(f"RSA key already exists at {local_key_path}")
            return str(local_key_path)
        
        # Parse SSH config to find the key
        ssh_config_path = Path.home() / ".ssh" / "config"
        if not ssh_config_path.exists():
            raise RuntimeError(f"SSH config not found at {ssh_config_path}")
        
        # Try to find the key path from SSH config
        key_path = self._parse_ssh_config_for_key(instance_id, ssh_config_path)
        
        # If not found, try to generate it with tnr connect
        if not key_path:
            print(f"No SSH config entry found for tnr-{instance_id}, attempting 'tnr connect {instance_id}'...")
            
            # Check if tnr command is available
            if not self._check_tnr_available():
                raise RuntimeError(
                    f"SSH config entry for tnr-{instance_id} not found and 'tnr' command not available. "
                    f"Please run 'tnr connect {instance_id}' on a machine with Thunder Compute CLI installed."
                )
            
            # Run tnr connect
            try:
                result = subprocess.run(
                    ["tnr", "connect", str(instance_id)],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                if result.returncode != 0:
                    raise RuntimeError(f"'tnr connect {instance_id}' failed: {result.stderr}")
                print(f"Successfully ran 'tnr connect {instance_id}'")
                
                # Re-parse SSH config
                key_path = self._parse_ssh_config_for_key(instance_id, ssh_config_path)
                if not key_path:
                    raise RuntimeError(
                        f"SSH config entry still not found after running 'tnr connect {instance_id}'"
                    )
            except subprocess.TimeoutExpired:
                raise RuntimeError(f"'tnr connect {instance_id}' timed out")
            except FileNotFoundError:
                raise RuntimeError("'tnr' command not found in PATH")
        
        # Verify the source key file exists
        source_key_path = Path(key_path)
        if not source_key_path.exists():
            raise RuntimeError(f"RSA key file not found at {source_key_path}")
        
        # Copy the key to secrets directory
        shutil.copy2(source_key_path, local_key_path)
        
        # Set appropriate permissions (read/write for owner only)
        os.chmod(local_key_path, 0o600)
        
        print(f"RSA key copied to {local_key_path}")
        return str(local_key_path)

    def _parse_ssh_config_for_key(self, instance_id: int, 
                                ssh_config_path: Path) -> Optional[str]:
        """
        Parse SSH config file to find IdentityFile for tnr-{instance_id}
        
        Args:
            instance_id: Thunder Compute instance ID
            ssh_config_path: Path to SSH config file
        
        Returns:
            Path to RSA key file, or None if not found
        """
        host_pattern = f"tnr-{instance_id}"
        
        try:
            with open(ssh_config_path, 'r') as f:
                lines = f.readlines()
            
            in_target_host = False
            for line in lines:
                line = line.strip()
                
                # Check if we're entering the target host section
                if line.startswith("Host "):
                    hosts = line[5:].strip().split()
                    in_target_host = host_pattern in hosts
                    continue
                
                # If we're in the target host section, look for IdentityFile
                if in_target_host and line.startswith("IdentityFile"):
                    # Extract the path (handle quotes)
                    match = re.match(r'IdentityFile\s+"?([^"]+)"?', line)
                    if match:
                        identity_file = match.group(1)
                        # Expand home directory if present
                        identity_file = os.path.expanduser(identity_file)
                        print(f"Found IdentityFile for tnr-{instance_id}: {identity_file}")
                        return identity_file
            
            return None
            
        except Exception as e:
            print(f"Error parsing SSH config: {e}")
            return None

    def _check_tnr_available(self) -> bool:
        """Check if 'tnr' command is available in PATH"""
        try:
            result = subprocess.run(
                ["which", "tnr"],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except:
            return False

    def setup_instance_keys(self, instance_ids: list[int],
                        secrets_dir: str = "./secrets",
                        force_refresh: bool = False) -> dict[int, str]:
        """
        Setup RSA keys for multiple instances at once
        
        Args:
            instance_ids: List of instance IDs
            secrets_dir: Local directory to store RSA keys
        
        Returns:
            Dictionary mapping instance_id to key_path
        """
        key_paths = {}
        
        for instance_id in instance_ids:
            try:
                key_path = self.ensure_rsa_key(instance_id, secrets_dir, force_refresh)
                key_paths[instance_id] = key_path
            except Exception as e:
                print(f"Warning: Failed to setup key for instance {instance_id}: {e}")
                key_paths[instance_id] = None
        
        return key_paths

    def get_ssh_config_info(self, instance_id: int) -> Optional[dict]:
        """
        Get complete SSH configuration info for a Thunder Compute instance
        
        Args:
            instance_id: Thunder Compute instance ID
        
        Returns:
            Dictionary with SSH config details, or None if not found
        """
        ssh_config_path = Path.home() / ".ssh" / "config"
        if not ssh_config_path.exists():
            return None
        
        host_pattern = f"tnr-{instance_id}"
        config_info = {
            'host': host_pattern,
            'hostname': None,
            'user': None,
            'identity_file': None,
            'port': 22
        }
        
        try:
            with open(ssh_config_path, 'r') as f:
                lines = f.readlines()
            
            in_target_host = False
            for line in lines:
                line = line.strip()
                
                # Check if we're entering the target host section
                if line.startswith("Host "):
                    hosts = line[5:].strip().split()
                    in_target_host = host_pattern in hosts
                    continue
                
                if in_target_host:
                    if line.startswith("HostName"):
                        config_info['hostname'] = line.split(None, 1)[1].strip()
                    elif line.startswith("User"):
                        config_info['user'] = line.split(None, 1)[1].strip()
                    elif line.startswith("IdentityFile"):
                        match = re.match(r'IdentityFile\s+"?([^"]+)"?', line)
                        if match:
                            config_info['identity_file'] = os.path.expanduser(match.group(1))
                    elif line.startswith("Port"):
                        config_info['port'] = int(line.split(None, 1)[1].strip())
            
            # Return None if we didn't find the essential info
            if not config_info['hostname'] or not config_info['identity_file']:
                return None
                
            return config_info
            
        except Exception as e:
            print(f"Error reading SSH config: {e}")
            return None

    def update_init_params_from_secrets(self, instance_id: int,
                                    secrets_dir: str = "./secrets") -> None:
        """
        Update the manager's SSH key path to use the local secrets directory
        
        Args:
            instance_id: Instance ID to configure for
            secrets_dir: Local secrets directory
        """
        # Ensure the key exists in secrets
        local_key_path = self.ensure_rsa_key(instance_id, secrets_dir)
        
        # Update the instance-specific key mapping
        self._instance_keys[instance_id] = local_key_path
        print(f"Updated SSH key path for instance {instance_id}: {local_key_path}")
    
    def list_instance_keys(self) -> Dict[int, str]:
        """
        List all SSH keys present in the secrets directory
        
        Returns:
            Dictionary mapping instance_id to key file path
        """
        keys = {}
        pattern = re.compile(r'id_rsa_instance_(\d+)')
        
        for file in self.secrets_dir.iterdir():
            match = pattern.match(file.name)
            if match:
                instance_id = int(match.group(1))
                keys[instance_id] = str(file)
        
        return keys

    def setup_all_instance_keys(self, force_refresh: bool = False) -> Dict[int, str]:
        """
        Setup SSH keys for all available instances
        
        Args:
            force_refresh: Force re-extraction even if keys exist
        
        Returns:
            Dictionary mapping instance_id to key_path
        """
        instances = self.list_instances()
        instance_ids = [int(iid) for iid in instances.keys()]
        
        return self.setup_instance_keys(instance_ids, str(self.secrets_dir), force_refresh)

    def cleanup_ssh_connections(self):
        """Close all SSH connections"""
        self.close_ssh()


# Example usage patterns with the updated per-instance key handling:
if __name__ == "__main__":
    # Method 1: Create manager that handles keys automatically
    manager = ThunderComputeManager()  # Will auto-setup keys as needed
    
    # Method 2: Using the convenience factory method
    manager = ThunderComputeManager.from_secrets()
    
    # Method 3: Disable auto key setup (manual key management)
    manager_manual = ThunderComputeManager(auto_setup_keys=False)
    
    # Connect to different instances - each uses its own key
    try:
        # Connect to instance 12345 (will auto-setup key if needed)
        ssh1 = manager.connect_ssh(12345)
        
        # Connect to instance 67890 (different key)
        ssh2 = manager.connect_ssh(67890)
        
        # List all available instance keys
        available_keys = manager.list_instance_keys()
        print(f"Available SSH keys: {available_keys}")
        
        # Validate setup for specific instances
        validation = manager.validate_secrets_setup(instance_ids=[12345, 67890])
        print(json.dumps(validation, indent=2))
        
        # Setup keys for all instances at once
        all_keys = manager.setup_all_instance_keys()
        print(f"Setup keys for instances: {list(all_keys.keys())}")
        
    finally:
        # Cleanup all SSH connections
        manager.cleanup_ssh_connections()

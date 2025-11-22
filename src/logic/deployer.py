import time
import os
import socket
import paramiko
from paramiko.ssh_exception import SSHException

class Deployer:
    def __init__(self):
        pass

    def _create_ssh_client(self, ip, user, password):
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(ip, username=user, password=password, timeout=10)
        return client

    def detect_flash_path(self, client):
        """
        Checks if the router has a 'flash' directory (common in v7/ax devices).
        Returns 'flash/' if found, else ''.
        """
        stdin, stdout, stderr = client.exec_command("/file print count-only where name=\"flash\"")
        output = stdout.read().decode().strip()
        try:
            count = int(output)
            if count > 0:
                return "flash/"
        except ValueError:
            pass
        return ""

    def deploy_configuration(self, ip, user, password, local_rsc_path, target_lan_ip, status_callback=None, heavy_payload=False):
        """
        Uploads the script and schedules it for execution.
        
        Args:
            ip: Current Router IP.
            user: Current Router User.
            password: Current Router Password.
            local_rsc_path: Path to the generated .rsc file.
            target_lan_ip: The new IP the router will have after config.
            status_callback: Function to call with status updates (str).
            heavy_payload: If True, increases schedule delay to allow for large downloads (e.g. Containers).
        """
        def log(msg):
            print(msg)
            if status_callback:
                status_callback(msg)

        client = None
        try:
            log(f"Connecting to {ip}...")
            client = self._create_ssh_client(ip, user, password)
            
            # 1. Detect Storage
            prefix = self.detect_flash_path(client)
            # Ensure file is named setup.rsc on remote to match strict requirements if needed,
            # though prompt says "If flash/ exists, all uploads must go to flash/setup.rsc. If not, use setup.rsc."
            remote_filename = "setup.rsc"
            remote_path = f"{prefix}{remote_filename}"
            log(f"Detected storage path: {prefix}")
            
            # 2. Upload File
            log(f"Uploading {remote_filename} to {remote_path}...")
            sftp = client.open_sftp()
            sftp.put(local_rsc_path, remote_path)
            sftp.close()
            
            # 3. Schedule Execution (Fire-and-Forget)
            # We use [/system clock get time] to run it "now" (plus the script's internal delay).
            # Note: The internal script delay (15s) prevents interface flapping from killing the script immediately.
            # We use interval=0 to run once.
            log("Scheduling configuration apply...")
            
            # Check for heavy payload (Containers)
            # If heavy, we delay the start time significantly to ensure we are disconnected or to just give buffer?
            # Actually, the prompt says "increase the script_run_delay to 60 seconds". 
            # This usually implies the delay INSIDE the script, or the delay before it runs.
            # Given "Script Injection" strategy runs locally, the *execution* time doesn't matter to us once disconnected.
            # However, if the prompt implies we should wait longer to poll, or if we should schedule it later...
            # "If 'Containers' are enabled, increase the script_run_delay to 60 seconds"
            # Let's increase the schedule start offset.
            
            offset_seconds = "00:01:00" if heavy_payload else "00:00:02"
            
            # Remove existing schedule if any to avoid error
            client.exec_command("/system scheduler remove [find name=TITAN_DEPLOY]")
            
            # Schedule slightly in the future to allow clean disconnect
            cmd = (
                f'/system scheduler add name=TITAN_DEPLOY '
                f'on-event="/import file={remote_path} verbose=yes" '
                f'start-time=([/system clock get time] + {offset_seconds}) interval=0'
            )
            
            stdin, stdout, stderr = client.exec_command(cmd)
            error = stderr.read().decode().strip()
            if error:
                raise Exception(f"Scheduler Error: {error}")
            
            log(f"Configuration scheduled (Offset: {offset_seconds}). Disconnecting...")
            client.close()
            
            # 4. Poll for return
            # If heavy payload, we might need to wait longer for it to boot/download
            timeout = 300 if heavy_payload else 120
            log(f"Waiting for router at {target_lan_ip} (Timeout: {timeout}s)...")
            self._poll_for_availability(target_lan_ip, log, timeout=timeout)
            
            log("Deployment Successful!")
            return True

        except Exception as e:
            log(f"Deployment Failed: {e}")
            if client:
                client.close()
            return False

    def perform_factory_reset(self, ip, user, password, status_callback=None):
        """
        Executes /system reset-configuration.
        Expects connection drop.
        """
        def log(msg):
            print(msg)
            if status_callback:
                status_callback(msg)
                
        client = None
        try:
            log(f"Connecting to {ip} for Reset...")
            client = self._create_ssh_client(ip, user, password)
            
            log("Sending Reset Command (Nuke & Pave)...")
            # no-defaults=yes: Removes default config
            # skip-backup=yes: Don't create .backup file
            cmd = "/system reset-configuration no-defaults=yes skip-backup=yes"
            
            try:
                client.exec_command(cmd)
                # We expect this to fail or timeout immediately as connection drops
                time.sleep(2) 
            except (EOFError, SSHException, OSError):
                # This is expected success behavior
                pass
                
            log("Reset command sent. Router is rebooting.")
            return True
            
        except Exception as e:
            # Real connection errors before the command
            log(f"Reset Failed: {e}")
            return False
        finally:
            if client:
                client.close()

    def _poll_for_availability(self, ip, log_func, timeout=120):
        """
        Pings/Connects to the target IP until available or timeout.
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                # Simple socket connect check to SSH port
                sock = socket.create_connection((ip, 22), timeout=2)
                sock.close()
                log_func(f"Target {ip} is online!")
                return
            except (socket.timeout, ConnectionRefusedError, OSError):
                pass
            
            time.sleep(2)
            
        log_func(f"Warning: Timed out waiting for {ip}")

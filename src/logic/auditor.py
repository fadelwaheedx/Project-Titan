import paramiko
import time

class RouterAuditor:
    """
    Connects to a MikroTik router via SSH and performs compliance checks.
    """
    def __init__(self):
        pass

    def _create_ssh_client(self, ip, user, password):
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            client.connect(ip, username=user, password=password, timeout=5)
            return client
        except Exception as e:
            print(f"SSH Connection Error: {e}")
            return None

    def run_compliance_scan(self, ip, user, password):
        """
        Runs the 'Gold Standard' rules check.
        Returns a report dictionary.
        """
        report = {
            "target_ip": ip,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "passed": True,
            "checks": []
        }
        
        client = self._create_ssh_client(ip, user, password)
        if not client:
            report["passed"] = False
            report["error"] = "Could not connect to device."
            return report

        try:
            # 1. User Check: Is user 'admin' present?
            # Command: /user print count-only where name="admin"
            stdin, stdout, stderr = client.exec_command('/user print count-only where name="admin"')
            count = stdout.read().decode().strip()
            check_admin = {
                "name": "Admin User Check",
                "description": "Checks if the default 'admin' user exists.",
                "status": "PASS"
            }
            if count == "1":
                check_admin["status"] = "FAIL"
                check_admin["details"] = "Default 'admin' user found. Disable or rename it."
                report["passed"] = False
            else:
                check_admin["details"] = "Default 'admin' user not found."
            report["checks"].append(check_admin)

            # 2. Service Check: Is telnet or www (HTTP) enabled?
            # Command: /ip service print count-only where (name="telnet" or name="www") and disabled=no
            # For simplicity via API, we check separately or use specific query if complex.
            # Let's check both.
            stdin, stdout, stderr = client.exec_command('/ip service print count-only where name="telnet" and disabled=no')
            count_telnet = stdout.read().decode().strip()
            
            stdin, stdout, stderr = client.exec_command('/ip service print count-only where name="www" and disabled=no')
            count_www = stdout.read().decode().strip()
            
            check_services = {
                "name": "Insecure Services Check",
                "description": "Checks if Telnet or HTTP (Unencrypted) are enabled.",
                "status": "PASS"
            }
            
            details = []
            if count_telnet == "1":
                details.append("Telnet ENABLED")
                report["passed"] = False
                check_services["status"] = "FAIL"
            
            if count_www == "1":
                details.append("HTTP (www) ENABLED")
                report["passed"] = False
                check_services["status"] = "FAIL"
                
            if not details:
                check_services["details"] = "Telnet and HTTP are disabled."
            else:
                check_services["details"] = ", ".join(details) + ". Disable them immediately."
            
            report["checks"].append(check_services)

            # 3. DNS Check: Is allow-remote-requests true?
            # Command: /ip dns get allow-remote-requests
            stdin, stdout, stderr = client.exec_command('/ip dns get allow-remote-requests')
            dns_remote = stdout.read().decode().strip()
            check_dns = {
                "name": "DNS Recursion Check",
                "description": "Checks if the router is acting as an open DNS resolver.",
                "status": "PASS"
            }
            if dns_remote == "true" or dns_remote == "yes":
                check_dns["status"] = "WARNING"
                check_dns["details"] = "DNS allow-remote-requests is TRUE. Ensure firewall protects UDP/53 from WAN."
                # Warning doesn't fail the whole report, just a flag
            else:
                check_dns["details"] = "DNS remote requests disabled."
            report["checks"].append(check_dns)

            # 4. FW Check: Does /ip firewall filter have a "Drop Input" rule?
            # Command: /ip firewall filter print count-only where action="drop" and chain="input"
            # This is a basic check; a robust one would check for specific interfaces, but count > 0 is a good start.
            stdin, stdout, stderr = client.exec_command('/ip firewall filter print count-only where action="drop" and chain="input"')
            fw_count = stdout.read().decode().strip()
            try:
                fw_count = int(fw_count)
            except:
                fw_count = 0
                
            check_fw = {
                "name": "Firewall Input Drop",
                "description": "Checks for at least one Drop rule in the Input chain.",
                "status": "PASS"
            }
            if fw_count == 0:
                check_fw["status"] = "FAIL"
                check_fw["details"] = "No DROP rules found in Input chain. Router Management is likely exposed."
                report["passed"] = False
            else:
                check_fw["details"] = f"Found {fw_count} drop rules in Input chain."
            report["checks"].append(check_fw)

        except Exception as e:
            report["passed"] = False
            report["error"] = f"Error during scan: {e}"
        finally:
            client.close()
            
        return report

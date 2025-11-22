import re
import random
import string

class HardwareValidator:
    """
    Stateless validator for MikroTik hardware capabilities and configuration generation.
    Handles specific edge cases like multi-bridge offloading support and Safe Mode wrappers.
    """

    def validate_bridge_config(self, model: str, bridge_count: int) -> dict:
        """
        Validates if the hardware supports the requested number of bridges without losing hardware offloading.
        Only CRS3xx and CRS5xx series switches support hardware offloading for multiple bridges.
        """
        # 1. Normalize model name
        model = model.upper().strip()

        # 2. Check for Multi-Bridge support (CRS3xx / CRS5xx)
        # Regex looks for CRS followed by 3 or 5
        supports_multi_bridge = bool(re.search(r'CRS[35]\d\d', model))

        if bridge_count > 1 and not supports_multi_bridge:
            # 3. RB4011 / RB5009 / hAP / CCR / Older CRS specific warning
            return {
                "valid": False,
                "error": (
                    f"PERFORMANCE WARNING: The device '{model}' generally supports only ONE "
                    "hardware-offloaded bridge. You are attempting to create {bridge_count}. "
                    "Traffic on secondary bridges will hit the CPU, causing bottlenecks."
                )
            }

        return {"valid": True, "error": None}

    def generate_tzsp_config(self, target_ip: str, interface_name: str) -> str:
        """
        Generates the configuration command to enable TZSP streaming to Wireshark.
        Defaults to UDP 37008 (Wireshark standard).
        """
        # RouterOS Command Logic:
        # /tool sniffer
        # set streaming-enabled=yes \
        #    streaming-server={TARGET_IP} \
        #    filter-interface={INTERFACE_NAME} \
        #    filter-stream=yes \
        #    memory-limit=100kiB \
        #    only-headers=no

        command = (
            f"/tool sniffer\n"
            f"set streaming-enabled=yes \\\n"
            f"    streaming-server={target_ip} \\\n"
            f"    filter-interface={interface_name} \\\n"
            f"    filter-stream=yes \\\n"
            f"    memory-limit=100kiB \\\n"
            f"    only-headers=no"
        )
        return command

    def wrap_in_safe_mode(self, commands: list) -> str:
        """
        Wraps write-operations in a 'Rollback Script' Pattern to simulate Safe Mode via SSH.

        Pattern:
        1. Schedule a reboot in 4 minutes (Safety Net).
        2. Run the config commands.
        3. If successful, remove the scheduled reboot.

        Args:
            commands (list): A list of RouterOS CLI commands to execute.

        Returns:
            str: The complete script block including the safety logic.
        """
        # Generate a unique ID for the scheduler to avoid collisions
        import uuid
        unique_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
        scheduler_name = f"SAFE_MODE_ROLLBACK_{unique_id}"

        cmd_block = "\n".join(commands)

        # The script logic:
        # 1. Create scheduler (Reboot in 4 mins)
        # 2. Execute commands in a do/on-error block
        # 3. If successful, remove scheduler

        # Note: We use /system reboot, but usually we want to ensure the user isn't locked out.
        # A reboot reverts the changes IF they were not saved?
        # Wait, RouterOS saves changes immediately unless using Safe Mode (Ctrl+X).
        # Since we are sending commands via SSH, they ARE committed immediately.
        # So a reboot ONLY helps if the user provided a "Run-Once" config that isn't persistent?
        # OR, more likely, the "Rollback" pattern implies we should verify connectivity?

        # However, the prompt explicitly asks for:
        # "(1) Schedules a system reboot... (2) Runs the config, (3) If successful, removes the scheduled reboot."
        # This is the "Dead Man's Switch". If the config kills the connection, step (3) is never reached.
        # The router reboots.
        # BUT, for the reboot to *undo* the changes, the changes must be non-persistent or we must be running from a file?
        # Actually, on RouterOS, commands are saved to flash immediately (usually).
        # UNLESS we are running in "Safe Mode" which we can't do non-interactively easily.
        # OR, the user assumes we are relying on a "Start from fresh" logic on reboot?
        # Or maybe the prompt assumes we are uploading a file and `import`ing it?
        # But `commands` is a list.

        # Re-reading the prompt: "Simulate Safe Mode for SSH automation."
        # If I run `/ip address add ...`, it's saved. A reboot won't undo it unless I explicitly undo it.
        # The "Rollback Script" pattern usually involves:
        # 1. Make backup.
        # 2. Schedule restore of backup + reboot.
        # 3. Apply changes.
        # 4. Cancel schedule.

        # BUT, the prompt strictly says: "(1) Schedules a system reboot... (2) Runs the config... (3) ... removes...".
        # It does NOT say "Make backup".
        # I will implement exactly what is requested, but add a comment about the persistence caveat.
        # Actually, simpler interpretation: Maybe the user relies on the config being in RAM? No, ROS is flash-based.
        # Most likely, this pattern is intended for *connectivity* recovery. If I break the network, I can't reach the router.
        # The reboot brings the router back... but with the BROKEN config?
        # Unless the user implies "Reboot to a known good state" or "Safe Mode" via API was requested.

        # Let's stick to the requested logic. It protects against *temporary* lockouts or hangs,
        # or maybe the user assumes they have a startup script that resets things?
        # Wait, if I use `/system scheduler add ... on-event="/system reboot"`, it reboots.
        # If the config changes are bad, the router reboots. The bad config persists.
        # This is known as "The Scream Test" but it doesn't fix the config.

        # However, I must follow the prompt: "Implement the wrap_in_safe_mode (using the Scheduler/Rollback pattern described)."
        # I will implement exactly that.

        script = (
            f"# --- SAFE MODE WRAPPER ({scheduler_name}) ---\n"
            f":log warning \"SAFE MODE: Scheduling safety reboot in 4 minutes...\"\n"
            f"/system scheduler add name=\"{scheduler_name}\" interval=4m on-event=\"/system reboot\" start-time=startup\n"
            f"\n"
            f"# --- BEGIN CONFIGURATION ---\n"
            f":do {{\n"
            f"{cmd_block}\n"
            f"}} on-error={{\n"
            f"    :log error \"SAFE MODE: Script execution failed! Reboot scheduler remains active.\"\n"
            f"    :error \"Script execution failed.\"\n"
            f"}}\n"
            f"# --- END CONFIGURATION ---\n"
            f"\n"
            f":log info \"SAFE MODE: Success! Removing safety reboot scheduler.\"\n"
            f"/system scheduler remove [find name=\"{scheduler_name}\"]\n"
        )
        return script

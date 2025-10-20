import datetime
import json
from pathlib import Path

from optiv_lib.config import AppConfig
from optiv_lib.providers.pan.ops import op, op_on_device
from optiv_lib.providers.pan.panorama.managed_devices.api import list_connected
from optiv_lib.providers.pan.session import PanoramaSession


def sanitize(branch: dict) -> None:
    """Recursively remove sensitive fields from nested PAN-OS config dicts."""
    sensitive_keys = {
        "pre-shared-key", "private-key", "public-key", "key",
        "bind-password", "password", "secret",
        "auth-password", "priv-password", "phash", "users"
    }

    for k, v in list(branch.items()):
        key_lower = k.lower()
        if any(token in key_lower for token in ("password", "secret", "key", "phash", "users")) \
           or key_lower in sensitive_keys:
            branch[k] = ""
        elif isinstance(v, dict):
            sanitize(v)
        elif isinstance(v, list):
            for item in v:
                if isinstance(item, dict):
                    sanitize(item)



def collect_devices(panorama, export):
    print("[1/3] Collecting device list from Panorama...")
    connected = list_connected(session=panorama)
    devices = connected.get("devices", {}).get("entry", [])
    print(f"  Found {len(devices)} connected devices.")

    for i, device in enumerate(devices, start=1):
        target = device["serial"]
        print(f"  ({i}/{len(devices)}) Collecting config from device {target}...")
        try:
            effective = op_on_device(
                session=panorama,
                cmd="<show><config><effective-running/></config></show>",
                target=target,
            )
            sanitize(effective)
            export[target] = effective
        except Exception as e:
            if 'password' not in e:
                print(f"Failed to collect {target}: {e}")
            else:
                print(f"Failed to collect {target}: <redacted for security reasons>")
                print(f"** Validate password is set correctly. **")
    print("  Device collection complete.")


def collect_panorama(panorama, export):
    print("[2/3] Collecting Panorama configuration...")
    panorama_effective = op(
        session=panorama,
        cmd="<show><config><candidate></candidate></config></show>",
    )
    sanitize(panorama_effective)
    export["panorama"] = panorama_effective
    print("  Panorama config collected.")


def write_json(export):
    print("[3/3] Writing export to JSON file...")
    timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    filename = f"export_{timestamp}.json"
    file_path = Path.cwd() / filename
    with open(file_path, "w") as f:
        json.dump(export, f, indent=2)
    print(f"  Export complete: {file_path}")


def main():
    config_path = Path.cwd() / "config.json"
    print("Starting Panorama config collector.")
    print(f"Looking for config file: {config_path}")
    if not config_path.exists():
        print("ERROR: config.json not found in current directory.")
        return

    print("Loading configuration...")
    cfg = AppConfig.from_json(config_path)

    print("Establishing Panorama session...")
    panorama = PanoramaSession(cfg)
    print("Connection established successfully.")

    export = {}
    collect_devices(panorama, export)
    collect_panorama(panorama, export)
    write_json(export)

    print("All tasks completed successfully.")


if __name__ == "__main__":
    main()

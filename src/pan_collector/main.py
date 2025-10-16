import datetime
import json
from pathlib import Path

from optiv_lib.config import AppConfig
from optiv_lib.providers.pan.ops import op, op_on_device
from optiv_lib.providers.pan.panorama.managed_devices.api import list_connected
from optiv_lib.providers.pan.session import PanoramaSession

def sanitize(branch):
    for k, v in branch.items():
        if k == 'users':
            branch[k] = ''
        elif 'password' in k:
            branch[k] = ''
        elif isinstance(v, dict):
            sanitize(v)
        elif isinstance(v, list):
            for item in v:
                if isinstance(item, dict):
                    sanitize(item)


def collect_devices(panorama, export):
    connected = list_connected(session=panorama)
    for device in connected['devices']['entry']:
        target = device['serial']
        effective = op_on_device(session=panorama, cmd="<show><config><effective-running/></config></show>", target=target)
        sanitize(effective)
        export[target] = effective


def collect_panorama(panorama, export):
    panorama_effective = op(session=panorama, cmd="<show><config><candidate></candidate></config></show>")
    sanitize(panorama_effective)
    export['panorama'] = panorama_effective


def write_json(export):
    timestamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    filename = f"export_{timestamp}.json"
    with open(filename, 'w') as f:
        json.dump(export, f)


def main():
    config_path = Path.cwd() / "config.json"
    print(f"Reading config from {config_path}")
    cfg = AppConfig.from_json(config_path)
    panorama = PanoramaSession(cfg)

    export = {}
    collect_devices(panorama, export)
    collect_panorama(panorama, export)
    write_json(export)


if __name__ == "__main__":
    main()

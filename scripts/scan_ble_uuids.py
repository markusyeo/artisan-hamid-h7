"""Print the GATT table of the roaster.

Connects to the first BLE device whose name starts with MATCHBOX and prints
its advertised services and every characteristic with its properties. Used to
identify the exact service and characteristic UUIDs in the native Artisan Hamid
driver (artisanlib.hamid), which otherwise must test candidate UART services.

To inspect the GATT table, power on the roaster, stop the bridge, and run:

    uv run scripts/scan_ble_uuids.py
"""

import asyncio

from bleak import BleakClient, BleakScanner

DEVICE_NAME_PREFIX = "MATCHBOX"


async def main() -> None:
    print(f"Scanning for {DEVICE_NAME_PREFIX}* ...")
    device = None
    devices = await BleakScanner.discover(timeout=10.0, return_adv=True)
    for bd, ad in devices.values():
        name = bd.name or ad.local_name
        if name and name.startswith(DEVICE_NAME_PREFIX):
            device = bd
            print(f"Found: {name} ({bd.address})")
            print(f"  advertised services: {ad.service_uuids}")
            break
    if device is None:
        print("No matching device found. Is the roaster on and the bridge stopped?")
        return

    async with BleakClient(device) as client:
        for service in client.services:
            print(f"service {service.uuid}  ({service.description})")
            for char in service.characteristics:
                print(f"  characteristic {char.uuid}  properties={sorted(char.properties)}")


if __name__ == "__main__":
    asyncio.run(main())

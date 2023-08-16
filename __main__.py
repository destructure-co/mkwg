import argparse
import os
import shutil
import sys
import subprocess
from string import Template

netdev_template = Template("""[NetDev]
Name=wg${id}
Kind=wireguard
Description=WireGuard tunnel wg${id}

[WireGuard]
ListenPort=5182${id}
PrivateKeyFile=/etc/systemd/network/wg${id}_private.key
""")

network_template = Template("""[Match]
Name=wg${id}

[Network]
Address=10.0.0.${id}/24
Address=fdc9:281f:04d7:9ee9::${id}/64
""")
                            
# TODO: finish this...
peer_template= Template("""[WireGuardPeer]
PublicKey=${pubkey}
PreSharedKeyFile=/etc/systemd/network/wg${network_id}.netdev.d/${peer_id}.psk
AllowedIPs=10.0.0.3/32
AllowedIPs=fdc9:281f:04d7:9ee9::3/128
""")
                            
def key_opener(path, flags):
    """An opener that sets the necessary file mode for wireguard keys"""
    return os.open(path, flags, mode=0o0640)

def init_network() -> None:
    """Initialize a new wireguard network"""
    if os.getuid() != 0:
        raise Exception("Must be root")

    # TODO: pass this in from an option
    id = 0

    # TODO: check if it already exists

    print("Creating wireguard network wg{0}...".format(id))

    with open("/etc/systemd/network/99-wg{0}.netdev".format(id), "w") as fh:
        fh.write(netdev_template.substitute({"id": id}))
        print(" [+] Created virtual network device {0}".format(fh.name))

    with open("/etc/systemd/network/99-wg{0}.network".format(id), "w") as fh:
        fh.write(network_template.substitute({"id": id}))
        print(" [+] Created network interface {0}".format(fh.name))

    dropin_dir = "/etc/systemd/network/99-wg{0}.netdev.d".format(id)
    os.makedirs(dropin_dir, mode=0o0750, exist_ok=True)
    print(" [+] Created drop-in directory {0}".format(dropin_dir))

    private_key = subprocess.run(["wg", "genkey"], check=True, capture_output=True).stdout

    with open("/etc/systemd/network/wg{0}_private.key".format(id), "w", opener=key_opener) as fh:
        fh.write(private_key.decode())
        shutil.chown(fh.name, "root", "systemd-network")
        print(" [+] Generated private key {0}".format(fh.name))

    public_key = subprocess.run(["wg", "pubkey"], input=private_key, check=True, capture_output=True).stdout

    with open("/etc/systemd/network/wg{0}_public.key".format(id), "w", opener=key_opener) as fh:
        fh.write(public_key.decode())
        shutil.chown(fh.name, "root", "systemd-network")
        print(" [+] Generated public key {0}".format(fh.name))
    
    subprocess.run(["networkctl", "reload"])
    print(" [-] Reloaded systemd-networkd")

def add_peer() -> None:
    """Add a wireguard peer to the given network"""

    # TODO: accept option
    network_id = 0

    # TODO: accept option for peer ID
    peer_id = "matt-allan"

    dropin_dir = "/etc/systemd/network/99-wg{0}.netdev.d".format(network_id)

    print("Creating wireguard peer {0} on network wg{1}...".format(peer_id, network_id))

    private_key = subprocess.run(["wg", "genkey"], check=True, capture_output=True).stdout

    public_key = subprocess.run(["wg", "pubkey"], input=private_key, check=True, capture_output=True).stdout

    with open(dropin_dir + "/{0}_public.key".format(peer_id), "w", opener=key_opener) as fh:
        fh.write(public_key.decode())
        shutil.chown(fh.name, "root", "systemd-network")
        print(" [+] Generated public key {0}".format(fh.name))

    with open(dropin_dir + "/peer-{0}.conf".format(peer_id), "w") as fh:
        fh.write(peer_template.substitute({
            "pubkey": "",
            "interface": "",
            "peer": "",
        }))
        print(" [+] Generated drop-in {0}".format(fh.name))

    # TODO: write conf to stdout, which can be qrencoded with a pipe

commands = {
    "init": init_network,
    "add": add_peer,
}

def main() -> int:
    """Invoke the command line application and return the exit code"""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command",
        choices=commands.keys(),
        nargs=1,
    )
    args = parser.parse_args()
    cmd = args.command[0]

    try:
        commands[cmd]()
        return 0
    except Exception as e:
        print("Error: ", e)
        return 1

if __name__ == "__main__":
    sys.exit(main())

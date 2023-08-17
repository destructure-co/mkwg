import argparse
import ipaddress
import json
import os
import shutil
import sys
import subprocess
from typing import TypedDict
import wg
from string import Template
from pathlib import Path
from configparser import ConfigParser
                            
# TODO: finish this...
peer_template= Template("""[WireGuardPeer]
PublicKey=${pubkey}
PreSharedKeyFile=/etc/systemd/network/wg${network_id}.netdev.d/${peer_id}.psk
AllowedIPs=10.0.0.3/32
AllowedIPs=fdc9:281f:04d7:9ee9::3/128
""")
                            
def gr_opener(path, flags):
    """An opener that sets the file mode to owner=rwx, group=r, other="""
    return os.open(path, flags, mode=0o0640)

class InitOptions(TypedDict):
    conf_dir: Path
    ifname: str
    port: int
    ip_net: ipaddress.IPv4Network | ipaddress.IPv6Network
    force: bool

def init_network(args: InitOptions) -> None:
    """Initialize a new wireguard network"""

    conf_dir: Path = args["directory"]
    ifname: str = args["interface"]
    # TODO: find next free port >= 51280 as default if not provided
    port: int = args["port"]
    ip_net: ipaddress.IPv4Network | ipaddress.IPv6Network = args["network"]
    force: bool = args["force"]

    if not ip_net.is_private:
        raise Exception(f"Network CIDR {ip_net} is not allocated for private networks (see RFC 1918 / RFC 4193)")

    if not os.access(conf_dir, os.W_OK):
        raise Exception(f"The directory {conf_dir} is not writeable (try sudo?)") 

    # Reload first to catch any new config files
    subprocess.run(["networkctl", "reload"], check=True)

    links = json.loads(subprocess.run(["networkctl", "list", "--json", "short"], capture_output=True).stdout)

    for iface in links["Interfaces"]:
        if iface["Name"] == ifname and not force:
            raise Exception(f"The interface {ifname} already exists (use --force to overwrite)")

    print(f"Creating wireguard network {ifname}...", file=sys.stderr)

    private_key = wg.genkey()

    netdev = ConfigParser()
    netdev.optionxform = lambda option: option
    netdev["NetDev"] = {
        "Name": ifname,
        "Kind": "wireguard",
        "Description": f"wireguard tunnel {ifname}",
    }

    netdev["WireGuard"] = {
        "ListenPort": port,
        "PrivateKey": private_key,
    }

    network = ConfigParser()
    network.optionxform = lambda option: option
    network["Match"] = {
        "Name": ifname,
    }
    network["Network"] = {
        "Address": str(ip_net),
    }

    # Write netdev
    with open(conf_dir / f"99-{ifname}.netdev", "w", opener=gr_opener) as fh:
        netdev.write(fh)
        shutil.chown(fh.name, "root", "systemd-network")
        print(f" [+] Created virtual network device {fh.name}", file=sys.stderr)

    with open(conf_dir / f"99-{ifname}.network", "w", opener=gr_opener) as fh:
        network.write(fh)
        shutil.chown(fh.name, "root", "systemd-network")
        print(f" [+] Created virtual network interface {fh.name}", file=sys.stderr)

    subprocess.run(["networkctl", "reload"])
    
    print(" [-] Reloaded systemd-networkd", file=sys.stderr)

# TODO: rewrite this
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

    with open(dropin_dir + "/{0}_public.key".format(peer_id), "w", opener=gr_opener) as fh:
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

def main() -> int:
    """Invoke the command line application and return the exit code"""
    parser = argparse.ArgumentParser(prog="mkwg")
    parser.add_argument("-C", "--directory", help="Root configuration directory", type=Path, default="/etc/systemd/network")
    parser.add_argument("-f", "--force", help="Force overwriting existing config", action=argparse.BooleanOptionalAction)
    subparsers = parser.add_subparsers(title="command", required=True)

    parser_init = subparsers.add_parser('init')
    parser_init.add_argument("-i", "--interface", help="Wireguard interface to create", default="wg0")
    parser_init.add_argument("-p", "--port", help="Wireguard interface listen port", type=int, default=51820)
    parser_init.add_argument("-n", "--network", help="IP network CIDR", type=ipaddress.ip_network, default="172.17.2.0/24")
    parser_init.set_defaults(func=init_network)

    args = parser.parse_args()

    try:
        args.func(vars(args))
        return 0
    except Exception as e:
        print("Error: ", e, file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())

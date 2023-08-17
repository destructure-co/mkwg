import argparse
import base64
import ipaddress
import urllib.request
import json
import os
import shutil
import sys
import subprocess
from typing import TypedDict
import wg
from pathlib import Path
from configparser import ConfigParser


def gr_opener(path, flags):
    """An opener that sets the file mode to owner=rwx, group=r, other="""
    return os.open(path, flags, mode=0o0640)


class InitOptions(TypedDict):
    directory: Path
    interface: str
    port: int
    network: ipaddress.IPv4Network | ipaddress.IPv6Network
    force: bool


def init_network(args: InitOptions) -> None:
    """Initialize a new wireguard network"""

    conf_dir = args["directory"]
    ifname = args["interface"]
    port = args["port"]
    ip_net = args["network"]
    force = args["force"]

    if not ip_net.is_private:
        raise Exception(
            f"Network CIDR {ip_net} is not allocated for private networks (see RFC 1918 / RFC 4193)"
        )

    if not os.access(conf_dir, os.W_OK):
        raise Exception(f"The directory {conf_dir} is not writeable (try sudo?)")

    # Reload first to catch any new config files
    subprocess.run(["networkctl", "reload"], check=True)

    links = json.loads(
        subprocess.run(
            ["networkctl", "list", "--json", "short"], capture_output=True
        ).stdout
    )

    for iface in links["Interfaces"]:
        if iface["Name"] == ifname and not force:
            raise Exception(
                f"The interface {ifname} already exists (use --force to overwrite)"
            )

    print(f"Creating wireguard network {ifname}...", file=sys.stderr)

    private_key = wg.genkey()

    # Use the first IP as the host
    wg_ip, *_ = ip_net.hosts()

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
        "Address": str(ipaddress.ip_network(wg_ip)),
    }
    network["Route"] = {
        "Gateway": str(wg_ip),
        "Destination": str(ip_net),
    }

    with open(conf_dir / f"99-{ifname}.netdev", "w", opener=gr_opener) as fh:
        netdev.write(fh, space_around_delimiters=False)
        shutil.chown(fh.name, "root", "systemd-network")
        print(f" [+] Created virtual network device {fh.name}", file=sys.stderr)

    with open(conf_dir / f"99-{ifname}.network", "w", opener=gr_opener) as fh:
        network.write(fh, space_around_delimiters=False)
        shutil.chown(fh.name, "root", "systemd-network")
        print(f" [+] Created virtual network interface {fh.name}", file=sys.stderr)

    subprocess.run(["networkctl", "reload"])

    print(" [-] Reloaded systemd-networkd", file=sys.stderr)


class AddOptions(TypedDict):
    directory: Path
    interface: str
    network: ipaddress.IPv4Network | ipaddress.IPv6Network
    force: bool
    name: str
    endpoint: str


def add_peer(args: AddOptions) -> None:
    """Add a wireguard peer to the given network"""

    conf_dir = args["directory"]
    name = args["name"]
    ip_peer = args["network"]
    ifname = args["interface"]
    force = args["force"]
    endpoint = args["endpoint"]

    print(f"Creating wireguard peer...", file=sys.stderr)

    if not os.access(conf_dir, os.W_OK):
        raise Exception(f"The directory {conf_dir} is not writeable (try sudo?)")

    dropin_dir = conf_dir / f"99-{ifname}.netdev.d"

    network_conf = ConfigParser()
    network_conf.read(conf_dir / f"99-{ifname}.network")

    ip_net = ipaddress.ip_network(network_conf["Network"]["Address"])

    netdev_conf = ConfigParser()
    netdev_conf.read(conf_dir / f"99-{ifname}.netdev")
    srv_key = netdev_conf["WireGuard"]["PrivateKey"]
    srv_port = netdev_conf["WireGuard"]["ListenPort"]

    if not dropin_dir.exists():
        dropin_dir.mkdir(0o755, parents=True, exist_ok=True)
        print(f" [+] Created drop-in directory {dropin_dir.name}", file=sys.stderr)

    if not ip_peer:
        ip_nets = []
        for f in dropin_dir.iterdir():
            if not f.is_file():
                continue
            peer_conf = ConfigParser()
            peer_conf.read(f)
            ip = peer_conf["WireGuardPeer"]["AllowedIPs"]
            if ip:
                ip_nets.append(ipaddress.ip_network(ip))
        if len(ip_nets) == 0:
            # Use the first available ip if no peers
            *_, last = ip_net.hosts()
            ip_peer = last + 1
        else:
            # Otherwise use the last peer's last IP in range + 1
            *_, last = ip_nets[-1].hosts()
            ip_peer = last + 1

    key = wg.genkey()
    pubkey = wg.pubkey(key)
    psk = wg.genpsk()

    if not name:
        name = base64.urlsafe_b64encode(base64.b64decode(pubkey)).decode("utf-8")

    peer = ConfigParser()
    peer.optionxform = lambda option: option
    peer["WireGuardPeer"] = {
        "PublicKey": pubkey,
        "PresharedKey": psk,
        "AllowedIPs": str(ipaddress.ip_network(ip_peer)),
    }

    with open(dropin_dir / f"peer-{name}.conf", "w", opener=gr_opener) as fh:
        peer.write(fh, space_around_delimiters=False)
        shutil.chown(fh.name, "root", "systemd-network")
        print(f" [+] Created peer {fh.name}", file=sys.stderr)

    subprocess.run(["networkctl", "reload"])

    print(" [-] Reloaded systemd-networkd", file=sys.stderr)

    srv_pubkey = wg.pubkey(srv_key)

    if not endpoint:
        with urllib.request.urlopen("http://icanhazip.com/") as f:
            pub_ip = f.read().decode("utf-8").strip()
            endpoint = f"{pub_ip}:{srv_port}"

    wg_conf = ConfigParser()
    wg_conf.optionxform = lambda option: option
    wg_conf["Interface"] = {
        "PrivateKey": key,
        "Address": str(ipaddress.ip_network(ip_peer)),
    }
    wg_conf["Peer"] = {
        "PublicKey": srv_pubkey,
        "PresharedKey": psk,
        "AllowedIPs": str(ip_net),
        "Endpoint": endpoint,
    }

    wg_conf.write(sys.stdout, space_around_delimiters=False)


def main() -> int:
    """Invoke the command line application and return the exit code"""
    parser = argparse.ArgumentParser(
        prog="mkwg", description="Manage wireguard networks"
    )
    parser.add_argument(
        "-C",
        "--directory",
        help="Root configuration directory",
        type=Path,
        default="/etc/systemd/network",
    )
    subparsers = parser.add_subparsers(title="command", required=True)

    parser_init = subparsers.add_parser("init")
    parser_init.add_argument(
        "-i", "--interface", help="Wireguard interface to create", default="wg0"
    )
    parser_init.add_argument(
        "-p", "--port", help="Wireguard interface listen port", type=int, default=51820
    )
    parser_init.add_argument(
        "-n",
        "--network",
        help="IP network CIDR",
        type=ipaddress.ip_network,
        default="172.17.2.0/24",
    )
    parser_init.add_argument(
        "-f",
        "--force",
        help="Force overwriting existing config",
        action=argparse.BooleanOptionalAction,
    )
    parser_init.set_defaults(func=init_network)

    parser_add = subparsers.add_parser("add")
    parser_add.add_argument(
        "-i", "--interface", help="Wireguard interface to add peer to", default="wg0"
    )
    parser_add.add_argument(
        "-n", "--network", help="IP network for peer", type=ipaddress.ip_network
    )
    parser_add.add_argument(
        "-f",
        "--force",
        help="Force overwriting existing config",
        action=argparse.BooleanOptionalAction,
    )
    parser_add.add_argument("-N", "--name", help="Peer name")
    parser_add.add_argument("-e", "--endpoint", help="Endpoint for peer connection")
    parser_add.set_defaults(func=add_peer)

    args = parser.parse_args()

    try:
        args.func(vars(args))
        return 0
    except Exception as e:
        print("Error: ", e, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

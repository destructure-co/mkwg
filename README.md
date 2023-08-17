# mkwg

A zero config CLI for managing Wireguard.

## Introduction

mkwg ("make wireguard") is a simple CLI tool for creating and managing a Wireguard VPN. It's an opinionated tool for creating "road warrior" VPNs, where you want to create a tunnel from one or more remote machines to a wireguard server in a cloud computing environment or office.

## Highlights

- Works out of the box on most linux distros with only the base packages
- No additional metadata to keep in sync - all state lives in the wireguard config files
- Sensible defaults for everything
- No web UI or daemon to secure

## System requirements

- `systemd-networkd`: Used to create the wireguard network interface. Included by default on any Ubuntu, Fedora, or RHEL based distro.
- `wireguard`: The wireguard kernel module needs to be installed and enabled. You don't need the wireguard tools (the `wg` commnd) though.
- `python`: A python 3 interpreter needs to be available. This should already be available on any VM since it's required by Cloud Init.
- `python3-cryptography`: Required to generate keys. Should be included by cloud-init already.

## Installation

You can download the latest release from the [releases page](https://github.com/destructure-co/mkwg/releases). Once you've downloaded the file, move it somewhere in your `$PATH` and ensure it's executable.

```
curl -L https://github.com/destructure-co/releases/download/0.1.0/mkwg
chmod +x mkwg
sudo mv mkwg /usr/local/bin
```

## Usage

### Create a network

To create a wireguard network with the default settings, just run `mkwg init`. You will need appropriate permissions to write the config files, which typically means using `sudo`.

```shell-session
$ sudo mkwg init
Creating wireguard network wg0...
 [+] Created virtual network device /etc/systemd/network/99-wg0.netdev
 [+] Created virtual network interface /etc/systemd/network/99-wg0.network
 [-] Reloaded systemd-networkd
```

### Add a peer

After creating the network you can add a peer. To add a peer call `mkwg add`. You don't have to provide any arguments but it's a good idea to specify a name for the peer with the `-N` / `--name` flag.

The command prints log messages to `stderr`, similar to the `init` command. A standard wireguard config file is written separately to `stdout` so you can pipe it to a file or a qr code. For example:

```shell-session
sudo mkwg add -N matt | qrencode -t ansiutf8
Creating wireguard peer...
 [+] Created peer /etc/systemd/network/99-wg0.netdev.d/peer-matt.conf
 [-] Reloaded systemd-networkd
████ ▄▄▄▄▄ █▀ ███▀▄ ▄█ █▄ ▄▄▄▀     █▀▄ ▄   █  ▄█▄▀▄ ██ ▄▄▄▄▄ ████
████ █   █ █▄▄ ▄███▀█▄▄▄█▀█▀ ▀████▄▄██▀█▄▀  █ ▀█▄ ▄ ██ █   █ ████
████ █▄▄▄█ █  ██ ▄█▄██▀▀ ▄▄▀▄▄ ▄▄▄  ▄ ▀▀▄█ ▀█ ▄▄  ▀▄██ █▄▄▄█ ████
████▄▄▄▄▄▄▄█ ▀ █▄▀ ▀ ▀▄▀ █▄█ ▀ █▄█ █▄█▄▀ ▀ █▄█▄▀ █ █ █▄▄▄▄▄▄▄████
████ ▄▀▄▀▀▄ ▀▀ ▀▄▄▀███▄█▄  █▄▀  ▄▄▄▀█▀ ▄  █▀▄██▄▀ █▄██▄▄▄▀  ▀████
█████▀ ▄▀▀▄█▄▀█▄▀▄ █▄ ▀▄▄▀█▄ ▄▀▄█▄▀▄ ▀▄█▄▄▀▀█▀█▀▀   ▄█▀ ▀ █ ▄████
████▀█ ██▀▄▄█▀ ▄█▄▄█▀▀▄▀▄█ █▄█    █▄ █ ▄ ▀▄█ ▄▄█ █▀▀▄▄▀ ▄▀  ▀████
...
```

Note that the private key will never be stored. You must pipe or copy it somewhere immediately.

### Manual administration

All this tool does is generate standard `systemd-networkd` config files. There is no additional metadata. To view the status of the link you can use `networkctl`, i.e.

```shell-session
networkctl status wg0
● 4: wg0
                     Link File: /usr/lib/systemd/network/99-default.link
                  Network File: /etc/systemd/network/99-wg0.network
                         State: routable (configured)
                  Online state: online
...
```

## Technical reference

By default every device receives an IP in the `172.17.2.x` range. The server where you run `mkwg` will be assigned `172.17.2.0`. The peers will be assigned incrementing IPs starting at `172.17.2.1`.

The server uses the default wireguard port 51280. The public IP address is fetched automatically unless the `--endpoint` option is specified.

Clients are only configured with the IP address of the server. It's not possible for clients to connect to each other directly.

The config files are written to `/etc/systemd/network` and are owned by `root:systemd-network` with 0640 permissons. When keys need to be stored they are included directly in the config file.

Each wireguard peer is stored as a separate config file in the drop-in directory for the network device. The peer name is used as the filename suffix. If a name is not specified a URL safe variant of the base64 encoding of the public key is used instead.

To avoid requiring the `wireguard-tools` package keys are generated in Python using the 
After generating new files systemd-networkd is reloaded with `networkctl reload`.

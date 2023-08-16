# mkwg

A zero config CLI for managing Wireguard.

## Introduction

mkwg ("make wireguard") is a simple CLI tool for creating and managing a Wireguard VPN. It's an opinionated tool for creating "road warrior" VPNs, where you want to create a tunnel from one or more remote machines to a wireguard server in a cloud computing environment or office.

## System requirements

- `systemd-networkd`: Used to create the wireguard network interface. Included by default on any Ubuntu, Fedora, or RHEL based distro.
- `wireguard`: The wireguard kernel module needs to be installed and enabled.
- `python`: A python 3 interpreter needs to be available, but you don't need any packages to be installed. Should already be available on any VM since it's required by Cloud Init.

## Installation

## Usage

### Create a network

```shell-session
$ mkwg init wg0
```

### List peers

```
$ mkwg list -i wg0
```

### Add a peer

```
$ mkwg add matt
```
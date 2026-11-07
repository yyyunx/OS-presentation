# Windows → existing VMware Ubuntu over SSH

Environment: Windows 11 Host, VMware Workstation Ubuntu 64-bit Guest, username
`ubuntu`, project `/mnt/hgfs/presentation/ticket-rush-os-demo`. Shared files are
the same Windows clone. SSH is optional remote control; the presentation's right
window remains a native Ubuntu Terminal running `make demo-proof`.

Windows OpenSSH Client was confirmed available (9.5). VMware Tools reported
Guest IP `192.168.139.128` and Host VMnet8 IP `192.168.139.1`. Addresses can change;
`hostname -I` in Ubuntu confirms the current Guest IP. Initial port 22 refused
connections; this is not a successful SSH session.

## One-time setup in Ubuntu Terminal

```bash
sudo apt update
sudo apt install -y openssh-server
sudo systemctl enable --now ssh
systemctl is-active ssh
hostname -I
```

Enter sudo/login passwords only at the local Ubuntu prompt, never into chat.
If UFW is active, allow the Windows Host (adjust IP if VMnet8 changes):

```bash
sudo ufw allow from 192.168.139.1 to any port 22 proto tcp
```

A task-specific Ed25519 key pair was prepared locally under the ignored
`.runtime/ssh/` directory. The private key stays on Windows and is never committed.
Install **only the public key** from the shared folder in Ubuntu:

```bash
mkdir -p ~/.ssh
chmod 700 ~/.ssh
touch ~/.ssh/authorized_keys
pub=/mnt/hgfs/presentation/ticket-rush-os-demo/.runtime/ssh/demo-proof_ed25519.pub
grep -qxFf "$pub" ~/.ssh/authorized_keys || cat "$pub" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

This public-key file is a local setup artifact, not a tracked repository file.
For a fresh clone, generate your own SSH key or use an existing trusted key.

## Verify from Windows PowerShell

From the Windows project root, using the current Guest IP:

```powershell
ssh -i .runtime/ssh/demo-proof_ed25519 -o IdentitiesOnly=yes -o BatchMode=yes -o ConnectTimeout=5 -o UserKnownHostsFile=.runtime/ssh/known_hosts ubuntu@192.168.139.128 id
```

The first connection records the SSH host key using the local VM's identified
address. A successful `id` result must precede claims of direct Ubuntu control.
Connection refused usually means sshd is not listening or a firewall rejects it;
Permission denied means the server is reachable but key authentication failed.

## Tests in Ubuntu (SSH or local Terminal)

Wait until the Dashboard has no active experiment; the tests need ports
8081/8082. The idle Dashboard controller on 8765 may remain open. Rebuild before
starting new experiments after source changes.

```bash
cd /mnt/hgfs/presentation/ticket-rush-os-demo
make
make test
make test-demo-ui
make test-demo-proof
```

These exact commands can be run manually if SSH is unavailable. A VMware shared
folder mounted noexec requires copying the whole source tree to a Guest home
directory and rebuilding there; use the same Guest clone for both presenter
Terminals. Restart the previously running Dashboard controller after updating
Python files, otherwise that process continues using its older loaded code.

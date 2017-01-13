from __future__ import absolute_import, division, print_function, unicode_literals

import os, sys

from .. import logger
from ..aws import resources
from .compat import subprocess

def new_ssh_key(bits=2048):
    from paramiko import RSAKey
    return RSAKey.generate(bits=bits)

def get_public_key_from_pair(key):
    return key.get_name() + " " + key.get_base64()

def key_fingerprint(key):
    return key.get_name() + " " + ":".join("{:02x}".format(ord(i)) for i in key.get_fingerprint())

def get_ssh_key_path(name):
    return os.path.expanduser("~/.ssh/{}.pem".format(name))

def ensure_ssh_key(name, verify_pem_file=True):
    from paramiko import RSAKey
    for key_pair in resources.ec2.key_pairs.all():
        if key_pair.name == name:
            if verify_pem_file and not os.path.exists(get_ssh_key_path(name)):
                msg = "Key {} found in EC2, but not in ~/.ssh."
                msg += " Delete the key in EC2, copy it to {}, or specify another key."
                raise KeyError(msg.format(name, get_ssh_key_path(name)))
            break
    else:
        if os.path.exists(get_ssh_key_path(name)):
            ssh_key = RSAKey.from_private_key_file(get_ssh_key_path(name))
        else:
            logger.info("Creating key pair %s", name)
            ssh_key = new_ssh_key()
            ssh_key.write_private_key_file(get_ssh_key_path(name))
        resources.ec2.import_key_pair(KeyName=name,
                                      PublicKeyMaterial=get_public_key_from_pair(ssh_key))
        logger.info("Imported SSH key %s", get_ssh_key_path(name))
    try:
        subprocess.check_call(["ssh-add", get_ssh_key_path(name)], timeout=5)
    except Exception as e:
        logger.warn("Failed to add %s to SSH keychain: %s. Connections may fail", get_ssh_key_path(name), e)
    return get_ssh_key_path(name)

def hostkey_line(hostnames, key):
    from paramiko import hostkeys
    return hostkeys.HostKeyEntry(hostnames=hostnames, key=key).to_line()

def add_ssh_host_key_to_known_hosts(host_key_line):
    ssh_known_hosts_path = os.path.expanduser("~/.ssh/known_hosts")
    with open(ssh_known_hosts_path, "a") as fh:
        fh.write(host_key_line)

def get_ssh_key_filename(args, base_name):
    if args.ssh_key_name is None:
        from getpass import getuser
        from socket import gethostname
        args.ssh_key_name = base_name + "." + getuser() + "." + gethostname().split(".")[0]
        return ensure_ssh_key(args.ssh_key_name)
    else:
        return ensure_ssh_key(args.ssh_key_name)

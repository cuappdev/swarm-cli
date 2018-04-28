# Docker Swarm - Command Line Interface Tool

This is a command line tool to setup and use a Docker Swarm cluster. It specifically provided the following operations:
- lockdown and secure each machine in the cluster
- install Docker and join each machine into the Swarm
- *(WIP)* deploy a Docker Stack to the Swarm
- boot up a testbed on which to test deployment

It uses Ansible to for provisioning the cluster. Ansible is incredibly flexible, but also is sensitive to relative paths of configuration files, playbooks, and other local files. In addition, using a Swarm cluster requires an inventory of hosts, SSH keys, and a Docker Compose file to specify deployment setup. As such, this project aims to separate files cleanly and provide a simple interface to configure deployments.

## Install

Install the following technologies on your system:
- [Python 3.5 or above](https://www.python.org/downloads/)
- [virtualenv](https://virtualenv.pypa.io/en/stable/)
- [Vagrant with Virtualbox](https://www.vagrantup.com/downloads.html)
- [Vagrant Virtualbox Guest Plugin](https://github.com/dotless-de/vagrant-vbguest)
- [Ansible](http://docs.ansible.com/ansible/latest/installation_guide/intro_installation.html)

Yes, you read that right. *Python 3.5 or above.* It's [current year](https://www.google.com/search?q=what+is+the+year) for Guido's sake.

In the project root, run the following:
```
virtualenv venv
source venv/bin/activate # On macOS and Linux
venv\Scripts\activate.bat # On Windows
pip install -r requirements.txt # in virtual environment
python manage.py # in virtual environment, run this command to check
```

### Windows

Ansible does not support Windows so far, and so you must run certain commands from within a Vagrant machine. A Vagrantfile for this machine has been provided.

## Configuration: swarm.ini

The `swarm.ini` file provides an interface to easily configure deployment information. A rundown of the file is as follows:

```
[Default]
UsingTestbed=true # Whether or not to deploy to the testbed
NetworkInterface=eth0 # The network interface over which cluster machines communicate for Docker Swarm
BuildDirectory=build # Relative path to ./bld in which to place compiled files
ComposeDirectory=docker-compose # Relative path to directory containing a Compose file
HostsFile=hosts # Relative path to Ansible inventory listing managers and workers in the swarm
PublicKeyFile=server.pem.pub # Relative path to a public SSH key
PrivateKeyFile=server.pem # Relative path to a private SSH key

[Testbed]
TestbedSize=5 # The number of nodes in the testbed
IPMask24=192.168.69 # The first 24 bits of the IP addresses to assign machines in the testbed
IPMask8Offset=50 # The offset of the lower 8 bits of the IP addresses to assign to machines
NetworkInterface=enp0s8 # The network interface over which testbed machines communicate
```

## Usage and Configuration Details

These are commands display information about the tool.

### `python manage.py`

This prints out a usage description with all commands and a short description of each one.

### `python manage.py config`

This prints out all the information that the tool uses based off of the contents of `swarm.ini`, including deduced absolute paths of important files and directories. This should be used every time the `swarm.ini` file is modified, to make sure the configuration are all correct.

## Testbed

This tool includes the option of booting up a testbed cluster of machines using Vagrant and Virtualbox. Each machine can take 5 - 7 minutes to create up, so it's best to keep the testbed size small, and not recompile it once the machines have been created.

### `python manage.py testbed compile`

This compiles the testbed using the parameters in the `swarm.ini` file. You should run this command *only if* you want to update the testbed. Recompiling will delete Vagrant metadata about machines that have been already created, which means the next `... testbed up` command will recreate the machines.

### `python manage.py testbed up`

This will boot up a compiled testbed. The script will crash if it hasn't been compiled already. If the testbed has been compiled but not created, this will create all the machines (which can take a while). If the testbed has been already created, it will boot up each machine one-by-one.

### `python manage.py testbed halt`

This will shutdown each machine in the testbed.

### `python manage.py testbed destroy`

This will destroy the the testbed.

## Swarm

These commands will provision a cluster of machines, locking down their access using SSH keys and joining them into a Docker Swarm.

### `python manage.py swarm compile`

This compiles the Ansible configuration, inventory, playbooks, and SSH keys into a single directory to ease deployment concerns and eliminate issues with relative paths. The Ansible deployment must be recompiled after every change to `swarm.ini`. Unlike with the testbed, it is safe to recompile whenever.

### `python manage.py swarm lockdown`

This locks down the cluster by creating an `appdev` user on all machines and disabling `root` login. In additon, it only allows traffic on the following ports:
- 22 TCP
- 80 TCP
- 443 TCP
- 2377 TCP
- 4789 UDP
- 7946 TCP/UDP

Since machines are locked down partially using the `root` user, you can only run this command *once* per cluster.

### `python manage.py swarm join`

This joins the machines listed in the Ansible inventory into the swarm. It will automatically start a new swarm if it doesn't exist, and join in new workers and managers if they weren't a part of it.
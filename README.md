# Docker Swarm - Command Line Interface Tool

This is a command line tool to setup and use a Docker Swarm cluster. It specifically provides the following operations:
- lockdown and secure each machine in the cluster
- install Docker and join each machine into the Swarm
- configure the Swarm to be ready for a Docker Stack
- boot up a testbed on which to test deployment

It uses Ansible to for provisioning the cluster. Ansible is incredibly flexible, but also is sensitive to relative paths of configuration files, playbooks, and other local files. In addition, using a Swarm cluster requires an inventory of hosts, SSH keys, and a Docker Compose file to specify deployment setup. As such, this project aims to separate files cleanly and provide a simple interface to configure deployments.

We compartmentalize the deployment information for each of our backends into *deployment bundles*. They contain the information related to the security of the cluster and the Docker Compose file.

## Install

Install the following technologies on your system:
- [Python 3.5 or above](https://www.python.org/downloads/)
- [virtualenv](https://virtualenv.pypa.io/en/stable/)
- [Vagrant with Virtualbox](https://www.vagrantup.com/downloads.html)
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

Once you've done that, copy `swarm.ini.in` to `swarm.ini`. You will use `swarm.ini` for configuration, whereas `swarm.ini.in` is the initial template.
```
cp swarm.ini.in swarm.ini
```

### Windows

Ansible does not support Windows at the moment, and so you must run certain commands from within a Vagrant machine. A Vagrantfile for this machine has been provided. Simply run `vagrant up` to boot up the machine and make sure that it is running when using this utility. The tool has been written such that if it detects it is on Windows, it will run the command inside the machine automatically. You won't ever need to SSH into the machine, but it will have some extra delay.

## Deployment bundles

A deployment bundle is a folder with the following contents and structure:

```
docker-compose/
  docker-compose.yml
  ...
domain.crt
hosts
server.pem
server.pem.pub
```

The `docker-compose` folder contains a production ready Docker Compose file `docker-compose.yml` that can be deployed to a Swarm. In this folder, any additional `Dockerfile`s must go here to build the images used in production.

The `domain.crt` is a TLS certificate for AppDev's private Docker Registry. This is what will allow our Swarms to pull prebuilt images of our services when we deploy or scale. This certificate lives in the `registry` bundle, which is a special bundle.

The `hosts` file is an Ansible inventory that lists the IPs of the machines we use to deploy. It is an INI-like file that is separated into to sections, `[manager]` and `[worker]`, where the machines whose IPs listed under each will become either a manager or worker node in the swarm.

The `server.pem` and `server.pem.pub` files are the private and public SSH keys for the machines. These are used to access the machines and setup testbeds to test deployments.


## Configuration: swarm.ini

The `swarm.ini` file (which you should have set up using `swarm.ini.in` - read the instructions) provides an interface to setup a testbed and determines whether or not the tool uses it. A rundown of the file is as follows:

```
[Testbed]
TestbedSize=5 # The number of nodes in the testbed
IPMask24=192.168.69 # The first 24 bits of the IP addresses to assign machines in the testbed
IPMask8Offset=50 # The offset of the lower 8 bits of the IP addresses to assign to machines
```

## Usage and Configuration Details

These are commands display information about the tool.

### `python manage.py`

This prints out a usage description with all commands and a short description of each one.

### `python manage.py compile <BUNDLE_DIR>`

This compiles the Ansible configuration, inventory, playbooks, security information, and Docker Compose setup into a single directory to ease deployment concerns and eliminate issues with relative paths. The Ansible deployment must be recompiled after every change to the bundle `BUNDLE_DIR`. 

This also compiles the testbed using the parameters in the `swarm.ini` file and the security information included in the bundle `BUNDLE_DIR`. Recompiling will delete Vagrant metadata about machines that have been already created, which means the next `python manage.py testbed up` command will recreate the machines. Keep this in mind, as this wastes space and can be a hassle to clean up later.

### `python manage.py config`

This prints out all the information that the tool uses based off of the contents of `swarm.ini`, including deduced absolute paths of important files and directories. This should be used every time the `swarm.ini` file is modified, to make sure the configuration are all correct.

## Testbed

This tool includes the option of booting up a testbed cluster of machines using Vagrant and Virtualbox. Each machine can take 2 - 5 minutes to create up, so it's best to keep the testbed size small, and not recompile it once the machines have been created.

### `python manage.py testbed up`

This will boot up a compiled testbed. The script will crash if it hasn't been compiled already. If the testbed has been compiled but not created, this will create all the machines (which can take a while). If the testbed has been already created, it will boot up each machine one-by-one.

### `python manage.py testbed halt`

This will shutdown each machine in the testbed.

### `python manage.py testbed destroy`

This will destroy the the testbed.

## Swarm

These commands will provision a cluster of machines, locking down their access using SSH keys and joining them into a Docker Swarm. They also can configure the Swarm to get ready for deployment, and also clean up Docker containers and images off of clusters.

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

### `python manage.py swarm configure`

This uploads the Docker Compose setup to the first manager in the Swarm, and installs the Docker Registry's TLS certificate on all the hosts. This allows us to deploy our backend on a manager, and all machines to access our private Registry.

### `python manage.py swarm clean`

This stops a Docker Stack (assumed to be called `the-stack`) and removes all containers and images from the Swarm.

## Swarm on the Testbed

The commands are slightly duplicated to easily operate on a running testbed.

### `python manage.py swarm-testbed [above command]`

This runs the Swarm operation `[above command]` on the testbed.

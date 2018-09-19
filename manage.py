import configparser
import distutils.dir_util
import math
import shutil
import subprocess
import sys
import os

import jinja2
import texttable

class Config:

  def __init__(self, bundle_path=None):
    self.config = configparser.ConfigParser()

    self.current_dir = os.path.dirname(os.path.abspath(__file__))

    self.config.read(os.path.join(self.current_dir, 'swarm.ini'))

    self.playbooks_dir = os.path.join(self.current_dir, 'playbooks')
    self.roles_dir = os.path.join(self.current_dir, 'roles')
    self.ansible_cfg_dir = os.path.join(self.current_dir, 'ansible-cfg')
    self.templates_dir = os.path.join(self.current_dir, 'templates')
    self.build_dir = os.path.join(self.current_dir, '.bld')

    if (bundle_path != None):
      self.bundle_dir = os.path.abspath(bundle_path)
    else:
      self.bundle_dir = self.build_dir

    self.compose_dir = os.path.join(self.bundle_dir, 'docker-compose')
    if (bundle_path != None):
      self.hosts_file = os.path.join(self.bundle_dir, 'hosts')

    self.public_key_file = os.path.join(self.bundle_dir, 'server.pem.pub')
    self.private_key_file = os.path.join(self.bundle_dir, 'server.pem')
    self.registry_crt_file = os.path.join(self.bundle_dir, 'domain.crt')

    self.testbed_dir = os.path.join(self.build_dir, 'testbed')
    self.testbed_size = int(self.config['Testbed']['TestbedSize'])
    self.ip_mask_24 = self.config['Testbed']['IPMask24']
    self.ip_mask_8_offset = int(self.config['Testbed']['IPMask8Offset'])

  def make_table(self):
    table = texttable.Texttable()
    table.add_rows(
        [
            ['Parameter', 'Value'],
            ['Current directory', self.current_dir],
            ['Playbooks directory', self.playbooks_dir],
            ['Roles directory', self.roles_dir],
            ['Ansible config directory', self.ansible_cfg_dir],
            ['Templates directory', self.templates_dir],
            ['Build directory', self.build_dir],
            ['', ''],
            ['Bundle directory', self.bundle_dir],
            ['Compose directory', self.compose_dir],
            ['Hosts file', self.hosts_file if self.hosts_file != None else ''],
            ['SSH public key file', self.public_key_file],
            ['SSH private key file', self.private_key_file],
            ['Registry TLS Certificate', self.registry_crt_file],
            ['', ''],
            ['Testbed directory', self.testbed_dir],
            ['Testbed size', str(self.testbed_size)],
            ['First 24 bits of testbed IPs', self.ip_mask_24],
            ['Offet of last 8 bits of testbed IPs', str(self.ip_mask_8_offset)]
        ]
    )
    return table

  def print_config(self):
    table = self.make_table()
    print(table.draw())

class Testbed:

  def __init__(self, config):
    self.config = config

    self.env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(self.config.current_dir),
        trim_blocks=True)
    self.template = self.env.get_template('templates/Vagrantfile.j2')
    self.template_context = {
        'TestbedSize': self.config.testbed_size,
        'IPMask24': self.config.ip_mask_24,
        'IPMask8Offset': self.config.ip_mask_8_offset
    }

    self.num_managers = math.ceil((self.config.testbed_size - 1) / 2)
    self.num_workers = self.config.testbed_size - self.num_managers

  def compile(self):
    if not os.path.exists(self.config.testbed_dir):
      os.makedirs(self.config.testbed_dir)
    else:
      shutil.rmtree(self.config.testbed_dir)
      os.makedirs(self.config.testbed_dir)

    template_outfile = os.path.join(self.config.testbed_dir, 'Vagrantfile')
    with open(template_outfile, 'w+') as f:
      f.write(self.template.render(self.template_context))

    hosts_outfile = os.path.join(self.config.testbed_dir, 'testbed_hosts')
    with open(hosts_outfile, 'w+') as f:
      for i in range(self.config.testbed_size):
        if i == 0:
          f.write('[manager]\n')
        elif i == self.num_managers:
          f.write('\n[worker]\n')

        ip_str = "%s.%s" % (
            self.config.ip_mask_24,
            str(i + 1 + self.config.ip_mask_8_offset))
        f.write(ip_str + '\n')

    shutil.copy(
        self.config.public_key_file,
        os.path.join(self.config.testbed_dir, 'server.pem.pub'))
    shutil.copy(
        self.config.private_key_file,
        os.path.join(self.config.testbed_dir, 'server.pem'))

  def up(self):
    subprocess.run(['vagrant', 'up', '--parallel'], cwd=self.config.testbed_dir)

  def halt(self):
    for i in range(self.config.testbed_size):
      node_str = 'node-'+str(i+1)
      subprocess.run(['vagrant', 'halt', node_str], cwd=self.config.testbed_dir)

  def destroy(self):
    subprocess.run(['vagrant', 'destroy', '-f'], cwd=self.config.testbed_dir)

class Swarm:

  def __init__(self, config):
    self.config = config

    if not os.path.exists(self.config.build_dir):
      os.makedirs(self.config.build_dir)

    self.vagrant_ssh_cmd = '"\
        rm -rf ~/deploy;\
        cp -r /deploy ~;\
        chmod 0400 ~/deploy/.bld/server.pem;\
        python3.5 ~/deploy/manage.py {0} {1}\
        "'

  def compile(self):
    shutil.copy(
        self.config.public_key_file,
        os.path.join(self.config.build_dir, 'server.pem.pub'))
    shutil.copy(
        self.config.private_key_file,
        os.path.join(self.config.build_dir, 'server.pem'))

    shutil.copy(
        self.config.registry_crt_file,
        os.path.join(self.config.build_dir, 'domain.crt'))

    distutils.dir_util.copy_tree(
        self.config.roles_dir,
        os.path.join(self.config.build_dir, 'roles'))

    distutils.dir_util.copy_tree(
        self.config.compose_dir,
        os.path.join(self.config.build_dir, 'docker-compose'))

    distutils.dir_util.copy_tree(
        self.config.playbooks_dir,
        self.config.build_dir)
    distutils.dir_util.copy_tree(
        self.config.ansible_cfg_dir,
        self.config.build_dir)

    if (self.config.hosts_file != None):
      shutil.copy(
          self.config.hosts_file,
          os.path.join(self.config.build_dir, 'production_hosts'))

  def use_proper_hosts(self, is_testbed):
    if is_testbed:
      shutil.copy(
          os.path.join(self.config.testbed_dir, 'testbed_hosts'),
          os.path.join(self.config.build_dir, 'hosts'))
    else:
      shutil.copy(
          os.path.join(self.config.build_dir, 'production_hosts'),
          os.path.join(self.config.build_dir, 'hosts'))

  def lockdown(self, is_testbed):
    if os.name == 'nt':
      subprocess.Popen(
          ['vagrant', 'ssh', '-c', self.vagrant_ssh_cmd.format(
              'swarm-testbed' if is_testbed else 'swarm', 'lockdown')
          ],
          cwd=self.config.current_dir).wait()
      return

    self.use_proper_hosts(is_testbed)
    temp_env = os.environ.copy()
    temp_env['ANSIBLE_CONFIG'] = 'root.cfg'
    subprocess.Popen(
        ['ansible-playbook', 'python-bootstrap.yml'],
        cwd=self.config.build_dir,
        env=temp_env).wait()
    if not is_testbed:
      subprocess.Popen(
          ['ansible-playbook', 'update-upgrade.yml'],
          cwd=self.config.build_dir,
          env=temp_env).wait()
    subprocess.Popen(
        ['ansible-playbook', 'install-docker.yml'],
        cwd=self.config.build_dir,
        env=temp_env).wait()
    subprocess.Popen(
        ['ansible-playbook', 'add-sudo-users.yml'],
        cwd=self.config.build_dir,
        env=temp_env).wait()

    temp_env['ANSIBLE_CONFIG'] = 'appdev.cfg'
    subprocess.Popen(
        ['ansible-playbook', 'security-lockdown.yml'],
        cwd=self.config.build_dir,
        env=temp_env).wait()

  def join(self, is_testbed):
    if os.name == 'nt':
      subprocess.Popen(
          ['vagrant', 'ssh', '-c', self.vagrant_ssh_cmd.format(
              'swarm-testbed' if is_testbed else 'swarm', 'join')
          ],
          cwd=self.config.current_dir).wait()
      return

    self.use_proper_hosts(is_testbed)
    temp_env = os.environ.copy()
    temp_env['ANSIBLE_CONFIG'] = 'appdev.cfg'
    subprocess.Popen(
        ['ansible-playbook', 'swarm-join.yml'],
        cwd=self.config.build_dir,
        env=temp_env).wait()

  def configure(self, is_testbed):
    if os.name == 'nt':
      subprocess.Popen(
          ['vagrant', 'ssh', '-c', self.vagrant_ssh_cmd.format(
              'swarm-testbed' if is_testbed else 'swarm', 'configure')
          ],
          cwd=self.config.current_dir).wait()
      return

    self.use_proper_hosts(is_testbed)
    temp_env = os.environ.copy()
    temp_env['ANSIBLE_CONFIG'] = 'appdev.cfg'
    subprocess.Popen(
        ['ansible-playbook', 'configure-stack.yml'],
        cwd=self.config.build_dir,
        env=temp_env).wait()

  def clean(self, is_testbed):
    if os.name == 'nt':
      subprocess.Popen(
          ['vagrant', 'ssh', '-c', self.vagrant_ssh_cmd.format(
              'swarm-testbed' if is_testbed else 'swarm', 'clean')
          ],
          cwd=self.config.current_dir).wait()
      return

    self.use_proper_hosts(is_testbed)
    temp_env = os.environ.copy()
    temp_env['ANSIBLE_CONFIG'] = 'appdev.cfg'
    subprocess.Popen(
        ['ansible-playbook', 'stack-down.yml'],
        cwd=self.config.build_dir,
        env=temp_env).wait()

def usage():
  print('''
AppDev Swarm CLI
Use this to setup, test, work with, and deploy to a Docker Swarm cluster.

Reference:
  python manage.py compile BUNDLE_DIR - compile the testbed and swarm tool using the bundle at path BUNDLE_DIR
  python manage.py config - print out the complete configuration described by the swarm.ini file and the curent compilation

Testbed Commands:
  python manage.py testbed up - boot up all nodes in the Vagrant testbed
  python manage.py testbed halt - power down all nodes in the Vagrant testbed
  python manage.py testbed destroy - destroy all nodes in the Vagrant testbed

Production Commands:
  python manage.py swarm lockdown - lock down access to the target production machines
  python manage.py swarm join - join the target machines into a Docker Swarm
  python manage.py swarm configure - upload the Docker Compose file to the first manager of the Swarm
  python manage.py swarm clean - remove Docker Stack, containers, and images from all machines

All production commands can be applied to Testbed machines by running:
  python manage.py swarm-testbed [command]
  ''')

def command():
  if len(sys.argv) == 1:
    usage()
    return
  config = Config()
  service = sys.argv[1]
  testbed = Testbed(config)
  swarm = Swarm(config)
  if service == 'compile':
    if len(sys.argv) != 3:
      usage()
      return
    config = Config(sys.argv[2])
    testbed = Testbed(config)
    swarm = Swarm(config)
    swarm.compile()
    testbed.compile()
  elif service == 'config':
    config.print_config()
  elif service == 'testbed':
    if len(sys.argv) == 2:
      usage()
      return
    option = sys.argv[2]
    if option == 'up':
      testbed.up()
    elif option == 'halt':
      testbed.halt()
    elif option == 'destroy':
      testbed.halt()
    else:
      usage()
  elif service == 'swarm' or service == 'swarm-testbed':
    if len(sys.argv) == 2:
      usage()
      return
    option = sys.argv[2]
    if option == 'lockdown':
      swarm.lockdown(service == 'swarm-testbed')
    elif option == 'join':
      swarm.join(service == 'swarm-testbed')
    elif option == 'configure':
      swarm.configure(service == 'swarm-testbed')
    elif option == 'clean':
      swarm.clean(service == 'swarm-testbed')
    else:
      usage()
  else:
    usage()

if __name__ == '__main__':
  command()

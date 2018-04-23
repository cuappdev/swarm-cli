import os, configparser, subprocess, shutil, sys, math, distutils.dir_util
from jinja2 import Environment, FileSystemLoader, Template

DRY_RUN = True

class Config:

  def __init__(self):
    self.config = configparser.ConfigParser()
    self.config.read('swarm.ini')

    self.current_dir = os.path.dirname(os.path.abspath(__file__))
    
    self.scripts_dir = os.path.join(self.current_dir, 'scripts')
    self.playbooks_dir = os.path.join(self.current_dir, 'playbooks')
    self.roles_dir = os.path.join(self.current_dir, 'roles')       
    self.ansible_cfg_dir = os.path.join(self.current_dir, 'ansible-cfg')
    self.vagrant_dir = os.path.join(self.current_dir, 'vagrant')
    self.bld_dir = os.path.join(self.current_dir, '.bld')

    self.using_testbed = bool(self.config['Default']['UsingTestbed'])
    self.build_dir = os.path.join(self.bld_dir, self.config['Default']['BuildDirectory'])
    self.compose_dir = os.path.join(self.current_dir, self.config['Default']['ComposeDirectory'])
    self.hosts_file = os.path.join(self.current_dir, self.config['Default']['HostsFile'])
    self.public_key_file = os.path.join(self.current_dir, self.config['Default']['PublicKeyFile'])
    self.private_key_file = os.path.join(self.current_dir, self.config['Default']['PrivateKeyFile'])

    self.testbed_dir = os.path.join(self.build_dir, 'testbed')
    self.testbed_size = int(self.config['Testbed']['TestbedSize'])
    self.ip_mask_24 = self.config['Testbed']['IPMask24']
    self.ip_mask_8_offset = int(self.config['Testbed']['IPMask8Offset'])
  
  def print_config(self):
    print("Current directory = " + self.current_dir)
    print("Scripts directory = " + self.scripts_dir)
    print("Playbooks directory = " + self.playbooks_dir)
    print("Roles directory = " + self.roles_dir)
    print("Ansible config directory = " + self.ansible_cfg_dir)
    print("Vagrant directory = " + self.vagrant_dir)
    print(".bld directroy = " + self.bld_dir)
    print("Using testbed? " + str(self.using_testbed))
    print("Build directory = " + self.build_dir)
    print("Compose directory = " + self.compose_dir)
    print("Hosts file = " + self.hosts_file)
    print("Public key file = " + self.public_key_file)
    print("Private key file = " + self.private_key_file)
    print("Testbed directory = " + self.testbed_dir)
    print("Testbed size = " + str(self.testbed_size))
    print("First 24 bits of testbed IPs = " + self.ip_mask_24)
    print("Offset of last 8 bits of testbed IPs = " + self.ip_mask_8_offset)    

class Testbed:

  def __init__(self):
    self.config = Config()
    
    self.env = Environment(
      loader=FileSystemLoader(self.config.current_dir), 
      trim_blocks=True)
    self.template = self.env.get_template('vagrant/Vagrantfile.j2')
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
    with open(template_outfile, 'w+') as file:
      file.write(self.template.render(self.template_context))
    
    hosts_outfile = os.path.join(self.config.testbed_dir, 'hosts')
    with open(hosts_outfile, 'w+') as file:
      for i in range(self.config.testbed_size):
        if i == 0: 
          file.write('[managers]\n')
        elif i == self.num_managers:
          file.write('\n[workers]\n')
        
        ip_str = self.config.ip_mask_24 + '.' + str(i + 1 + self.config.ip_mask_8_offset)
        file.write(ip_str + '\n')
    
    shutil.copyfile(
      self.config.public_key_file, 
      os.path.join(self.config.testbed_dir, 'server.pem.pub'))
    shutil.copyfile(
      self.config.private_key_file, 
      os.path.join(self.config.testbed_dir, 'server.pem'))

  def ensure_compiled(self):
    template_outfile = os.path.join(self.config.testbed_dir, 'Vagrantfile')
    hosts_outfile = os.path.join(self.config.testbed_dir, 'hosts')

    if not os.path.exists(template_outfile) \
      or not os.path.exists(hosts_outfile):
      self.compile()
  
  def up(self):
    self.ensure_compiled()
    subprocess.run(['vagrant', 'up'], cwd=self.config.testbed_dir)

  def halt(self):
    self.ensure_compiled()
    for i in range(self.config.testbed_size):
      node_str = 'node-'+str(i+1)
      subprocess.run(['vagrant', 'halt', node_str], cwd=self.config.testbed_dir)

  def destroy(self):
    self.ensure_compiled()
    subprocess.run(['vagrant', 'destroy', '-f'], cwd=self.config.testbed_dir)  

class Swarm:

  def __init__(self):
    self.testbed = Testbed()
    self.config = self.testbed.config
    
    if not os.path.exists(self.config.build_dir):
      os.makedirs(self.config.build_dir)
    
    if self.config.using_testbed:
      self.hosts_buildfile = os.path.join(self.config.testbed_dir, 'hosts')
      self.initial_ansible_config = 'vagrant.cfg'
    else:
      self.hosts_buildfile = self.config.hosts_file
      self.initial_ansible_config = 'droplet.cfg'      

  def compile(self):
    shutil.copy(
      self.config.public_key_file, 
      os.path.join(self.config.build_dir, 'server.pem.pub'))
    shutil.copy(
      self.config.private_key_file, 
      os.path.join(self.config.build_dir, 'server.pem'))
    os.chmod(os.path.join(self.config.build_dir, 'server.pem'), 400)
    
    distutils.dir_util.copy_tree(
      self.config.roles_dir, 
      os.path.join(self.config.build_dir, 'roles'))

    distutils.dir_util.copy_tree(
      self.config.playbooks_dir,
      self.config.build_dir)
    distutils.dir_util.copy_tree(
      self.config.ansible_cfg_dir,
      self.config.build_dir)
    
    shutil.copy(
      self.hosts_buildfile,
      os.path.join(self.config.build_dir, 'hosts'))
  
  def provision(self):
    temp_env = os.environ.copy()
    
    temp_env['ANSIBLE_CONFIG'] = self.initial_ansible_config
    subprocess.Popen(
      ['ansible-playbook', 'python-bootstrap.yml'], 
      cwd=self.config.build_dir, 
      env=temp_env).wait()
    if not self.config.using_testbed:
      subprocess.Popen(
        ['ansible-playbook', 'update-upgrade.yml'], 
        cwd=self.config.build_dir, 
        env=temp_env).wait()
    subprocess.Popen(
      ['ansible-playbook', 'add-sudo-users.yml'], 
      cwd=self.config.build_dir, 
      env=temp_env).wait()
    
    temp_env['ANSIBLE_CONFIG'] = 'deploy.cfg'  
    subprocess.Popen(
      ['ansible-playbook', 'security-lockdown.yml'], 
      cwd=self.config.build_dir, 
      env=temp_env).wait()
    subprocess.Popen(
      ['ansible-playbook', 'install-docker.yml'], 
      cwd=self.config.build_dir, 
      env=temp_env).wait()
      
def usage():
  print("Swarm CLI tool\n")
  print("Use this tool to setup, test, work with, and deploy to a Docker Swarm cluster.\n")
  print("REFERENCE")
  print("python manage.py config - print out the complete configuration of the tool described by the swarm.ini file")
  print("")
  print("python manage.py testbed compile - compile the Vagrant testbed in order to launch some test nodes")
  print("python manage.py testbed up - boot up all nodes in the Vagrant testbed")
  print("python manage.py testbed halt - power down all nodes in the Vagrant testbed")
  print("python manage.py testbed destroy - destroy all nodes in the Vagrant testbed")  
  print("")
  print("python manage.py swarm compile - compile the Ansible setup necessary to provision and deploy to the target machines")  
  print("python manage.py swarm provision - provision the target machines using the Ansible setup")  
  
def command():
  if len(sys.argv) == 1:
    usage()
    return
  swarm = Swarm()
  testbed = swarm.testbed
  config = swarm.config
  service = sys.argv[1]
  if service == 'config':
    config.print_config()
  elif service == 'testbed':
    if len(sys.argv) == 2:
      usage()
      return
    option = sys.argv[2]
    if option == 'compile':
      testbed.compile()
    elif option == 'up':
      testbed.up()
    elif option == 'halt':
      testbed.halt()
    elif option == 'destroy':
      testbed.halt()
    else:
      usage()
  elif service == 'swarm':
    if len(sys.argv) == 2:
      usage()
      return
    option = sys.argv[2]
    if option == 'compile':
      swarm.compile()
    elif option == 'provision':
      swarm.provision()
    else:
      usage()
  else:
    usage()

if __name__ == '__main__':
  command()
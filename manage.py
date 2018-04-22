import os, configparser, subprocess, shutil, sys
from jinja2 import Environment, FileSystemLoader, Template

def read_config():
  config = configparser.ConfigParser()
  config.read('swarm.ini')
  return config

def current_dir():
  return os.path.dirname(os.path.abspath(__file__))

def scripts_dir():
  return os.path.join(
    current_dir(), 
    'scripts')

def playbooks_dir():
  return os.path.join(
    current_dir(), 
    'scripts')

def cfg_ansible_dir():
  return os.path.join(
    current_dir(), 
    'cfg-ansible')

def testbed_dir(config):
  return os.path.join(
    current_dir(), 
    'bld', 
    config['Default']['BuildDirectory'], 
    'testbed')

def keyfiles(config):
  pubfile = os.path.join(
    current_dir(), 
    config['Default']['PublicKeyFile'])
  privfile = os.path.join(
    current_dir(), 
    config['Default']['PrivateKeyFile'])
  return (pubfile, privfile)

def ensure_dir_exists(dirname):
  if not os.path.exists(dirname):
    os.makedirs(dirname)

def compile_testbed():
  config = read_config()
  env = Environment(
    loader=FileSystemLoader(current_dir()), 
    trim_blocks=True)
  vgfile_template = env.get_template('vagrantfiles/Vagrantfile.j2')
  
  vgfile_contents = vgfile_template.render(
    TestbedSize=config['Testbed']['TestbedSize'],
    IPMask24=config['Testbed']['IPMask24'],
    IPMask8Offset=config['Testbed']['IPMask8Offset'])
  
  testbed_build_dir = testbed_dir(config)
  vgfile_filename = os.path.join(testbed_build_dir, 'Vagrantfile')
  vgfile_hostsfile = os.path.join(testbed_build_dir, 'hosts')

  ensure_dir_exists(testbed_build_dir)
  with open(vgfile_filename, 'w+') as vgfile_out:
    vgfile_out.write(vgfile_contents)

  with open(vgfile_hostsfile, 'w+') as vgfile_hosts:
    testbed_size = int(config['Testbed']['TestbedSize'])
    ipmask8offset = int(config['Testbed']['IPMask8Offset'])
    
    for i in range(testbed_size):
      ip_str = config['Testbed']['IPMask24'] + '.' + str(i + 1 + ipmask8offset)
      vgfile_hosts.write(ip_str + '\n')
  
  (pubfile, privfile) = keyfiles(config)

  shutil.copyfile(pubfile, os.path.join(testbed_build_dir, 'server.pem.pub'))
  shutil.copyfile(privfile, os.path.join(testbed_build_dir, 'server.pem'))
  # shutil.copyfile(
  #   os.path.join(scripts_dir(), 'new-ssh-keys.sh'),
  #   os.path.join(testbed_build_dir, 'new-ssh-keys.sh'))

def boot_up_testbed():
  config = read_config()
  testbed_build_dir = testbed_dir(config)
  vgfile_filename = os.path.join(testbed_build_dir, 'Vagrantfile')
  vgfile_hostsfile = os.path.join(testbed_build_dir, 'hosts')

  if not (os.path.exists(vgfile_filename) 
      and os.path.exists(vgfile_hostsfile)):
    compile_testbed()

  subprocess.run(['vagrant', 'up'], cwd=testbed_build_dir)

def halt_testbed():
  config = read_config()
  testbed_build_dir = testbed_dir(config)
  vgfile_filename = os.path.join(testbed_build_dir, 'Vagrantfile')
  vgfile_hostsfile = os.path.join(testbed_build_dir, 'hosts')

  if not (os.path.exists(vgfile_filename) 
      and os.path.exists(vgfile_hostsfile)):
    compile_testbed()  

  testbed_size = int(config['Testbed']['TestbedSize'])
  for i in range(testbed_size):
    subprocess.run(['vagrant', 'halt', 'node-'+str(i+1)], cwd=testbed_build_dir)  

def destroy_testbed():
  config = read_config()
  testbed_build_dir = testbed_dir(config)
  vgfile_filename = os.path.join(testbed_build_dir, 'Vagrantfile')
  vgfile_hostsfile = os.path.join(testbed_build_dir, 'hosts')

  if not (os.path.exists(vgfile_filename) 
      and os.path.exists(vgfile_hostsfile)):
    compile_testbed()  

  subprocess.run(['killall', '-9', 'vagrant'], cwd=testbed_build_dir)  
  subprocess.run(['killall', '-9', 'ruby'], cwd=testbed_build_dir)    
  subprocess.run(['vagrant', 'destroy', '-f'], cwd=testbed_build_dir)  

def command():
  service = sys.argv[1]
  if service == 'testbed' and len(sys.argv) >= 3:
    option = sys.argv[2]
    if option == 'compile':
      compile_testbed()
    elif option == 'up':
      boot_up_testbed()
    elif option == 'down':
      halt_testbed()
    elif option == 'destroy':
      destroy_testbed()
    else:
      print("using testbed service but did not provide valid option")
  else:
    print("im walkin heeeerreee!!!")

if __name__ == '__main__':
  command()
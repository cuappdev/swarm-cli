import os, configparser
from jinja2 import Environment, FileSystemLoader, Template

def read_config():
  config = configparser.ConfigParser()
  config.read('swarm.ini')
  return config

def render_vagrantfile():
  config = read_config()
  current_dir = os.path.dirname(os.path.abspath(__file__))
  env = Environment(loader=FileSystemLoader(current_dir), trim_blocks=True)
  vgfile_template = env.get_template("vagrantfiles/Vagrantfile.j2")
  print(vgfile_template.render(
    TestbedSize=config['Testbed']['TestbedSize'],
    IPMask24=config['Testbed']['IPMask24'],
    IPMask8Offset=config['Testbed']['IPMask8Offset']
  ))

if __name__ == '__main__':
  render_vagrantfile()
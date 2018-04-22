import os
from jinja2 import Environment, FileSystemLoader, Template

def render_vagrantfile(testbed_size, ipmask_24, ipmask_8_offs):
  current_dir = os.path.dirname(os.path.abspath(__file__))
  env = Environment(loader=FileSystemLoader(current_dir), trim_blocks=True)
  vagrantfile = env.get_template("vagrantfiles/Vagrantfile.jinja2")
  print(vagrantfile.render(
    testbed_size=testbed_size,
    ipmask_24=ipmask_24,
    ipmask_8_offs=ipmask_8_offs
  ))

if __name__ == '__main__':
  render_vagrantfile(1, "192.168.69", 50)
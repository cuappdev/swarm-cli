# A Vagrant box to deploy from using Ansible, for Windows users

Vagrant.configure("2") do |config|

  # Ubuntu 16.04
  config.vm.box = "bento/ubuntu-16.04"
  
  # Enable an internet connection
  config.vm.network "private_network", type: "dhcp"
  
  # Enable shared folder
  config.vm.synced_folder ".", "/deploy"

  # Install Ansible
  config.vm.provision "shell", inline: <<-SHELL
    sudo apt-get update
    sudo apt-get install -y software-properties-common
    sudo apt-add-repository -y ppa:ansible/ansible
    sudo apt-get update
    sudo apt-get install -y ansible
  SHELL

end
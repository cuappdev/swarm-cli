#! /bin/bash

N=2

vagrant ssh node-1 -c "bash /vagrant/scripts/get-ip.sh > /vagrant/hosts"
if [ $N -gt 1 ]
then

i=2
while [  $i -le $N ]; do
  vagrant ssh node-$i -c "bash /vagrant/scripts/get-ip.sh >> /vagrant/hosts"  
  let i=i+1 
done

fi

sed -i -e '/^Connection/ d' hosts

vagrant ssh node-1 -c "bash /vagrant/scripts/new-ssh-keys.sh"

if [ $N -gt 1 ]
then

i=2
while [  $i -le $N ]; do
   vagrant ssh node-$i -c "bash /vagrant/scripts/new-ssh-keys.sh"
   let i=i+1 
done

fi

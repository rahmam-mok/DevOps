#vi jenkinsinstall.sh
#chmod +x jenkinsinstall.sh
#then past the following to teh jenkinsinstall.sh then save the file and run ./jenkinsinstall.sh
sudo yum install wget git java-1.8.0-openjdk -y
sudo wget -O /etc/yum.repos.d/jenkins.repo \
    https://pkg.jenkins.io/redhat-stable/jenkins.repo
sudo rpm --import https://pkg.jenkins.io/redhat-stable/jenkins.io.key
sudo yum upgrade
# Add required dependencies for the jenkins package
sudo amazon-linux-extras install java-openjdk11
sudo yum install jenkins
sudo systemctl daemon-reload

sudo systemctl enable jenkins

sudo systemctl start jenkins
sudo systemctl status jenkins

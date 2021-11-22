# setting up environment for new machine



# install python3.7
sudo apt update
sudo apt install software-properties-common
sudo add-apt-repository ppa:deadsnakes/ppa
# Press [ENTER] to continue or Ctrl-c to cancel adding it.Copy
sudo apt install python3.7
sudo apt-get update && sudo apt-get install python3-pip

# installing libraries
python3.7 -m pip install virtualenv
python3.7 -m virtualenv try
source try/bin/activate
wget https://files.pythonhosted.org/packages/f2/e2/813dff3d72df2f49554204e7e5f73a3dc0f0eb1e3958a4cad3ef3fb278b7/sentencepiece-0.1.91-cp37-cp37m-manylinux1_x86_64.whl .
python3.7 -m pip install sentencepiece-0.1.91-cp37-cp37m-manylinux1_x86_64.whl

python3.7 -m pip install cdqa

# updating version of pandas 
python3.7 -m pip uninstall numpy
python3.7 -m pip install numpy==1.19.5
python3.7 -m pip install bs4

python3.7 -c "from cdqa.utils.download import download_model; download_model(model='bert-squad_1.1', dir='./models')"

# Installing java for tika server 
sudo apt update
sudo apt install default-jdk # Confirm the installation by typing y (yes) and press Enter.
sudo apt update
sudo apt install default-jre
sudo apt install software-properties-common
sudo add-apt-repository ppa:linuxuprising/java
sudo apt update
sudo apt install oracle-java11-installer


# installing web scrapper librairies
source try/bin/activate
python3.7 -m pip install selenium
sudo apt-get update 
sudo apt install chromium-chromedriver -q
# VPN-Switcher
A MacOS menubar app to switch ExpressVPN servers on a DD-WRT router.
The router needs to be manually configured with an ExpressVPN ovpn file and SSH access needs to be enabled.


## Installation
`git clone https://github.com/comiconomenclaturist/VPN-Switcher.git`
`cd VPN-Switcher`
`pip install -r requirements.txt`
`python setup.py py2app`

Then copy `./dist/VPN Switcher.app` to the Applications folder.
import rumps
import os
import re
import json
import subprocess
import shutil


class Location:
    COUNTRY_CODES = json.loads(open("country_codes.json", "r", encoding="utf-8").read())

    def __init__(self, file):
        self.file = file
        regex = re.compile(
            r"my_expressvpn_(?P<country>\w+)(?:_-_)?(?P<region>\w+)?(?:_-_(?P<number>\d))?_udp\.ovpn"
        )
        match = re.match(regex, os.path.basename(file))
        if match:
            self.country = (match.group("country") or "").upper().replace("_", " ")
            self.region = (match.group("region") or "").title().replace("_", " ")
            self.number = match.group("number") or ""

    @property
    def name(self):
        c = self.country
        for countries in self.COUNTRY_CODES.values():
            for country in countries.values():
                if country.lower() == self.country.lower():
                    c = country
        text = " - ".join(filter(None, [c, self.region]))
        if self.number:
            return f"{self.flag} {text} [{self.number}]"
        return f"{self.flag} {text}"

    @property
    def server(self):
        for line in open(self.file).readlines():
            if line.startswith("remote "):
                server = line.split()[1]
                return server

    @property
    def flag(self):
        for countries in self.COUNTRY_CODES.values():
            for code, name in countries.items():
                if name.lower() == self.country.lower():
                    box = lambda ch: chr(ord(ch) + 0x1F1A5)
                    return box(code[0]) + box(code[1])
        return ""

    @property
    def continent(self):
        for continent, countries in self.COUNTRY_CODES.items():
            for country in countries.values():
                if country.lower() == self.country.lower():
                    return continent
        return "Misc"

    def __str__(self):
        return self.name


class VPNSwitcher(rumps.App):
    def __init__(self):
        super(VPNSwitcher, self).__init__("VPN Switcher")
        self.icon = "icon_1024_x_1024_white.png"
        self.template = True
        self.app_dir = rumps.application_support(self.name)
        self.preferences = os.path.join(self.app_dir, "preferences.json")
        self.conf = os.path.join(self.app_dir, "conf/")

        os.makedirs(self.conf, exist_ok=True)

        if not os.path.isfile(self.preferences):
            self.set_preferences()

        self.pref = json.loads(open(self.preferences, "r").read())

    def about(self, _):
        rumps.alert(
            title="VPN Switcher",
            message="""
                This app switches Express VPN servers on a DD-WRT router.
                You must have SSH access, and have copied your SSH key to the router
                """,
        )

    def set_preferences(self, _, data={}):
        window = rumps.Window(dimensions=(100, 20), cancel=True)
        window.title = "Configure the VPN Switcher for SSH access to your DD-WRT router"
        fields = {
            "IP address": self.get_default_gateway_ip(),
            "SSH port": 22,
            "username": "root",
        }
        for field, default in fields.items():
            window.default_text = default
            window.message = f"Enter the router's {field}:"
            response = window.run()
            if not response.clicked:
                return
            data[field] = response.text
        f = open(self.preferences, "w")
        f.write(json.dumps(data))
        f.close()

    def add_location(self, _):
        window = rumps.Window(dimensions=(300, 50), cancel=True)
        window.title = "Import Express VPN ovpn file"
        window.message = "Drag and drop a file here"
        response = window.run()
        if response.clicked and response.text:
            file = shutil.copy(response.text, self.conf)
            location = Location(file)
            locations = self.menu.get("Locations")

            if not locations.get(location.continent):
                locations.add(rumps.MenuItem(location.continent, None))
            if location not in locations.get(location.continent):
                locations.get(location.continent).add(
                    rumps.MenuItem(location, callback=app.switch)
                )

    def get_locations(self):
        for root, dirs, files in os.walk(self.conf):
            files.sort()
            for f in files:
                if f.endswith(".ovpn"):
                    yield Location(os.path.join(root, f))

    def get_current(self):
        response = self.run_commands("nvram get openvpncl_remoteip")
        if response.stdout:
            server = "".join(chr(x) for x in response.stdout).strip()
            locations = self.menu.get("Locations")

            for location in self.get_locations():
                if location.server == server:
                    for key in locations.keys():
                        if location.continent == key:
                            for loc in locations.get(key):
                                if loc == location.name:
                                    locations[key][loc].state = 1
                                    return

    def get_default_gateway_ip(self):
        response = subprocess.run(
            ["route", "-n", "get", "default"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if not response.stderr:
            stdout = "".join(chr(x) for x in response.stdout).strip()
            for line in stdout.splitlines():
                if line.strip().startswith("gateway"):
                    return line.split(":")[1].strip()

    def run_commands(self, commands):
        response = subprocess.run(
            [
                "ssh",
                "-qp",
                self.pref["SSH port"],
                f"{self.pref['username']}@{self.pref['IP address']}",
                commands,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        return response

    def switch(self, location):
        for loc in self.get_locations():
            if loc.name == location.title:
                commands = [
                    "stopservice openvpn",
                    f"nvram set openvpncl_remoteip={loc.server}",
                    "nvram commit",
                    "startservice openvpn",
                ]
                commands = "; ".join(commands)
                response = self.run_commands(commands)
                locations = self.menu.get("Locations")

                if not response.stderr:
                    for key in locations.keys():
                        if isinstance(locations[key], rumps.MenuItem):
                            for country in locations[key].keys():
                                if country == location.title:
                                    locations[key][country].state = 1
                                else:
                                    locations[key][country].state = 0


app = VPNSwitcher()
app.menu = [
    rumps.MenuItem("About", callback=app.about),
    rumps.MenuItem("Preferences", callback=app.set_preferences),
    [
        rumps.MenuItem("Locations"),
        [
            rumps.MenuItem("Add", callback=app.add_location),
            None,
        ],
    ],
    None,
]

for location in app.get_locations():
    if not app.menu.get("Locations").get(location.continent):
        app.menu.get("Locations").add(rumps.MenuItem(location.continent, None))
    app.menu.get("Locations").get(location.continent).add(
        rumps.MenuItem(location, callback=app.switch),
    )

app.get_current()


if __name__ == "__main__":
    app.run()

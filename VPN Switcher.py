import rumps
import os
import json
import subprocess
import shutil
from location import Location


class VPNSwitcher(rumps.App):
    def __init__(self):
        super(VPNSwitcher, self).__init__("VPN Switcher")
        self.icon = "icon_1024_x_1024_white.png"
        self.template = True
        self.app_dir = rumps.application_support(self.name)
        self.preferences = os.path.join(self.app_dir, "preferences.json")
        self.conf = os.path.join(self.app_dir, "conf/")
        self.recent = os.path.join(self.app_dir, "recent.json")

        os.makedirs(self.conf, exist_ok=True)

        if not os.path.isfile(self.preferences):
            self.set_preferences(None)

        if os.path.exists(self.preferences):
            self.pref = json.loads(open(self.preferences, "r").read())
        else:
            self.pref = None

    def about(self, _):
        rumps.alert(
            title="VPN Switcher",
            message="""
                This app switches Express VPN servers on a DD-WRT router.
                You must have SSH access, and have copied your SSH key to the router
                """,
        )

    def set_preferences(self, _, data={}):
        window = rumps.Window(
            dimensions=(100, 20),
            cancel=True,
            title="Configure the VPN Switcher for SSH access to your DD-WRT router",
        )
        fields = {
            "IP address": self.get_default_gateway(),
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
        window = rumps.Window(
            dimensions=(300, 50),
            cancel=True,
            title="Import Express VPN ovpn file",
            message="Drag and drop a file here",
        )
        response = window.run()
        if response.clicked and response.text:
            file = shutil.copy(response.text, self.conf)
            self._add_location(Location(file))

    def _add_location(self, location):
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

    def get_location(self, location):
        locations = self.menu.get("Locations")

        for region in locations.keys():
            if region not in ["Add", "Recent"]:
                if isinstance(locations[region], rumps.MenuItem):
                    for country in locations[region].keys():
                        if country == location:
                            return (region, country)

    def get_current(self):
        response = self.run_commands("nvram get openvpncl_remoteip")
        if response and response.stdout:
            server = "".join(chr(x) for x in response.stdout).strip()

            for location in self.get_locations():
                if location.server == server:
                    region, country = self.get_location(location.name)
                    self.menu.get("Locations")[region][country].state = 1
                    self.current = country
                    self.menu.add(rumps.MenuItem(country))
                    self.menu.get(self.current).state = 1

    def add_recent(self, country):
        countries = []

        if os.path.exists(self.recent):
            countries = json.loads(open(self.recent, "r").read())
            countries.reverse()

            if country in countries:
                countries.remove(country)

        countries.append(country)
        countries.reverse()

        self.menu.get("Locations").get("Recent").clear()
        recent = self.menu.get("Locations").get("Recent")

        for c in countries[:5]:
            recent.add(rumps.MenuItem(c, callback=app.switch))
        recent.get(country).state = 1

        open(self.recent, "w").write(json.dumps(countries[:5]))

    def set_recent(self):
        recent = self.menu.get("Locations").get("Recent")

        if os.path.exists(self.recent):
            for country in json.loads(open(self.recent, "r").read()):
                recent.add(rumps.MenuItem(country, callback=app.switch))
                if country == self.current:
                    recent.get(self.current).state = 1

    def get_default_gateway(self):
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
        if self.pref:
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

    def switch(self, menu_item):
        for location in self.get_locations():
            if location.name == menu_item.title:
                commands = [
                    "stopservice openvpn",
                    f"nvram set openvpncl_remoteip={location.server}",
                    "nvram commit",
                    "startservice openvpn",
                ]
                commands = "; ".join(commands)
                response = self.run_commands(commands)

                if response and not response.stderr:
                    region, country = self.get_location(menu_item.title)
                    previous_region, previous_country = self.get_location(
                        self.menu.get(self.current).title
                    )
                    self.menu.get("Locations")[region][country].state = 1
                    self.menu.get(self.current).title = country
                    self.menu.get(self.current).state = 1
                    self.menu.get("Locations")[previous_region][
                        previous_country
                    ].state = 0
                    self.add_recent(country)
                    return


app = VPNSwitcher()
app.menu = [
    rumps.MenuItem("About", callback=app.about),
    rumps.MenuItem("Preferences", callback=app.set_preferences),
    [
        rumps.MenuItem("Locations"),
        [
            rumps.MenuItem("Add", callback=app.add_location),
            None,
            [rumps.MenuItem("Recent"), [None]],
            None,
        ],
    ],
    None,
]

for location in app.get_locations():
    app._add_location(location)

app.get_current()
app.set_recent()

if __name__ == "__main__":
    app.run()

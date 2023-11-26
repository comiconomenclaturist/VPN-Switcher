import json
import re
import os


class Location:
    COUNTRY_CODES = json.loads(open("country_codes.json", "r", encoding="utf-8").read())

    def __init__(self, file):
        self.file = file
        self.region = "Misc"
        self.country = ""
        self.flag = ""

        regex = re.compile(
            r"my_expressvpn_(?P<country>\w+)(?:_-_)?(?P<area>\w+)?(?:_-_(?P<number>\d))?_udp\.ovpn"
        )
        match = re.match(regex, os.path.basename(file))
        if match:
            self.country = (match.group("country") or "").upper().replace("_", " ")
            self.area = (match.group("area") or "").title().replace("_", " ")
            self.number = match.group("number") or ""

        if self.country:
            for region, countries in self.COUNTRY_CODES.items():
                for code, country in countries.items():
                    if country.lower() == self.country.lower():
                        self.region = region
                        self.country = country
                        box = lambda ch: chr(ord(ch) + 0x1F1A5)
                        self.flag = box(code[0]) + box(code[1])

    @property
    def title(self):
        text = " - ".join(filter(None, [self.country, self.area]))
        if self.number:
            return f"{self.flag} {text} [{self.number}]"
        return f"{self.flag} {text}"

    @property
    def server(self):
        for line in open(self.file).readlines():
            if line.startswith("remote "):
                server = line.split()[1]
                return server

    def __str__(self):
        return self.title

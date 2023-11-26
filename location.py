import json
import re
import os


class Location:
    COUNTRY_CODES = json.loads(open("country_codes.json", "r", encoding="utf-8").read())

    def __init__(self, file):
        self.file = file
        self.continent = "Misc"
        self.country = ""
        self.flag = ""

        regex = re.compile(
            r"my_expressvpn_(?P<country>\w+)(?:_-_)?(?P<region>\w+)?(?:_-_(?P<number>\d))?_udp\.ovpn"
        )
        match = re.match(regex, os.path.basename(file))
        if match:
            self.country = (match.group("country") or "").upper().replace("_", " ")
            self.region = (match.group("region") or "").title().replace("_", " ")
            self.number = match.group("number") or ""

        if self.country:
            for continent, countries in self.COUNTRY_CODES.items():
                for code, country in countries.items():
                    if country.lower() == self.country.lower():
                        self.continent = continent
                        self.country = country
                        box = lambda ch: chr(ord(ch) + 0x1F1A5)
                        self.flag = box(code[0]) + box(code[1])

    @property
    def name(self):
        text = " - ".join(filter(None, [self.country, self.region]))
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
        return self.name

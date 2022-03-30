from config import Settings as S
import requests
import subprocess

'''
field1 - battery capacity
field2 - battery voltage
field3 - AC Voltage
field4 - Online status
'''


class APIWriter:
    def __init__(self, api_key):
        self.write_endpoint = "https://api.thingspeak.com/update"
        self.api_key = api_key

    def send_data(self, **kwargs):
        payload = {"api_key": self.api_key}
        payload.update(kwargs)
        r = requests.get(self.write_endpoint, params=payload)
        return r.status_code


class upscOutParser:
    def __init__(self, ups_name):
        self.stdout_raw = ""
        self.stdout = {}
        self.ups_name = ups_name
        self.get_and_convert_stdout()

    def get_and_convert_stdout(self):
        proc = subprocess.Popen(["upsc", self.ups_name], stdout=subprocess.PIPE)
        self.stdout_raw = proc.stdout.readlines()
        for byteline in self.stdout_raw:
            line = byteline.decode("utf-8")
            key, value = line.split(": ")
            self.stdout.update({key: value.rstrip("\n")})
        self.normalize_digits()
        self.convert_online_status()

    def normalize_digits(self):
        digits_fields = [
            "battery.charge",
            "battery.charge.low",
            "battery.charge.warning",
            "battery.runtime",
            "battery.runtime.low",
            "battery.voltage",
            "battery.voltage.nominal",
            "driver.parameter.pollfreq",
            "driver.parameter.pollinterval",
            "input.transfer.high",
            "input.transfer.low",
            "input.voltage",
            "input.voltage.nominal",
            "ups.delay.shutdown",
            "ups.load",
            "ups.timer.reboot",
            "ups.timer.shutdown"
        ]
        for field in digits_fields:
            _new_item = float(self.stdout[field])
            self.stdout.update({field: _new_item})

    def convert_online_status(self):
        # todo: someday add "ups.status: OL CHRG LB" as 0.5 value, or maybe thingspeak add some states, not only values
        bool_status_name = "ups.status.isonline"
        _val = self.stdout["ups.status"][0:2]
        if _val == "OL":
            self.stdout.update({bool_status_name: 1})
        else:
            self.stdout.update({bool_status_name: 0})

    def get_stdout(self):
        return self.stdout

    def get_stdout_values(self, *args):
        if not args:
            return self.get_stdout()
        else:
            _picked_dict = {}
            for item in args:
                try:
                    _picked_dict.update({item:self.stdout[item]})
                except KeyError:
                    pass
            return _picked_dict


if __name__ == '__main__':
    needed_values = ["battery.charge",
                    "battery.voltage",
                    "input.voltage",
                    "ups.status.isonline"]
    data_to_send = {}
    read_values = upscOutParser(S.UPS_NAME).get_stdout_values(*needed_values)
    i = 1
    for item in needed_values:
        data_to_send.update({f'field{i}': read_values[item]})
        i += 1

    APIWriter(S.WRITE_API_KEY).send_data(**data_to_send)

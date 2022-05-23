from config import Settings as S
import requests
import subprocess
import logging
from time import sleep
from requests.exceptions import RequestException
'''
field1 - battery capacity
field2 - battery voltage
field3 - AC Voltage
field4 - Online status
'''

logging.basicConfig(format=u'%(filename) s[LINE:%(lineno)d]# %(levelname)-8s [%(asctime)s]  %(message)s',
                    level=logging.INFO, filename=u'error.log')


class APIWriter:
    def __init__(self, api_key):
        self.write_endpoint = "https://api.thingspeak.com/update"
        self.api_key = api_key
        self.number_retries = 3
        self.retries_timeout = 10

    def send_data(self, **kwargs):
        payload = {"api_key": self.api_key}
        payload.update(kwargs)
        try:
            r = requests.get(self.write_endpoint, params=payload)
            logging.info(f'API Health: status code: {r.status_code}, text: {r.text}')
        except RequestException as e:
            logging.error(f"request error: {e}")
            for i in range(self.number_retries):
                r = requests.get(self.write_endpoint, params=payload)
                if r.status_code == 200:
                    break
                else:
                    logging.error("didn't help")
                sleep(self.retries_timeout)


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
        _val = self.stdout["ups.status"]
        if _val == "OL":
            self.stdout.update({bool_status_name: 1})
        elif _val == "OL CHRG LB":
            self.stdout.update({bool_status_name: 0.3})
        elif _val == "OL CHRG":
            self.stdout.update({bool_status_name: 0.5})
        elif _val == "OB DISCHRG":
            self.stdout.update({bool_status_name: 0})
        elif _val == "OL CHRG RB":
            self.stdout.update({bool_status_name: -1})

    def get_stdout(self):
        return self.stdout

    def get_stdout_values(self, *args):
        if not args:
            return self.get_stdout()
        else:
            _picked_dict = {}
            for arg in args:
                try:
                    _picked_dict.update({arg: self.stdout[arg]})
                except KeyError:
                    pass
            return _picked_dict


if __name__ == '__main__':
    data_to_send = {}
    read_values = upscOutParser(S.UPS_NAME).get_stdout_values(*S.needed_values)
    i = 1
    logging.info(read_values)
    for item in S.needed_values:
        data_to_send.update({f'field{i}': read_values[item]})
        i += 1

    APIWriter(S.WRITE_API_KEY).send_data(**data_to_send)

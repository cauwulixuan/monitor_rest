#!/usr/bin/python
#-*- coding:utf-8 -*-

import re, os
import logging
import requests
from pprint import pprint


logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s',
                    datefmt='%a, %d %b %Y %H:%M:%S')
import sys
logger = logging.getLogger(sys.path[0] + 'service_metrics')

def get_ip(consul_ip, consul_port, service_name):
    url = 'http://{0}:{1}/v1/catalog/node/{2}'.format(consul_ip, consul_port, service_name)
    response = requests.get(url)
    pprint(response.json())

def main():
    consul_ip = "10.10.6.206"
    consul_port = 8500
    service_name = "prometheus"
    get_ip(consul_ip, consul_port, service_name)

if __name__ == '__main__':
    main()


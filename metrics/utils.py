#!/usr/bin/python
#-*- coding:utf-8 -*-

import re, os
import monitor_params
import logging
import requests

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s',
                    datefmt='%a, %d %b %Y %H:%M:%S')
import sys
logger = logging.getLogger(sys.path[0] + 'utils')

def get_instances(ip, port):
    ip_list = []
    instances = []
    if r',' in ip.strip():
        try:
            list = re.split(r'[,\s]\s*', ip.strip())
            print list
        except:
            logging.error("Can't split ip: {0}. Check the ip {0} in monitor_params.py.".format(ip))
            sys.exit(1)
        else:
            ip_list = list
    else:
        ip_list.append(ip.strip())
        
    for i in range(len(ip_list)):
        url = ip_list[i] + ":" + port
        instances.append(url)

    print instances
    return instances

def prometheus_url():
    instances = get_instances(monitor_params.prometheus_ip, monitor_params.prometheus_port)
    success = 0
    for i in range(len(instances)):
        url = 'http://{0}/api/v1/query'.format(instances[i])
        param = {
            "query": 'prometheus_build_info{{instance="{0}"}}'.format(instances[i])
        }
        logging.info("start GET %s?%s", url, param)
        try:
            response = requests.get(url, params=param)
            response.raise_for_status()
        except requests.exceptions.ConnectionError:
            logging.error("GET %s?%s failed! Connection Error.", url, param)
            continue
        except requests.RequestException as e:
            logging.error(e)
            continue
        else:
            logging.info("GET /api/v1/query?%s ok! Response code is = %s", param, response.status_code)
            success += 1
            return url            
    if not success:
        logging.error("No prometheus url available, please check prometheus.")
        sys.exit(1)
    

def grafana_url():
    prom_url = prometheus_url()
    instances = get_instances(monitor_params.grafana_ip, monitor_params.grafana_port)
    outside_instances = get_instances(monitor_params.grafana_outside_ip, monitor_params.grafana_port)
    success = 0
    for i in range(len(instances)):
        param = {
            "query": 'grafana_info{{instance="{0}"}}'.format(instances[i])
        }
        logging.info("start GET %s?%s", prom_url, param)
        response = requests.get(prom_url, params=param)
        if response.status_code != requests.codes.ok:
            logging.error("GET %s?%s failed! The error code is: %s", prom_url, param, response.status_code)
            continue
        else:
            logging.info("GET /api/v1/query?%s ok! Response code is = %s", param, response.status_code)
            success += 1
            return outside_instances[i]

    if not success:
        logging.error("No grafana url available, please check! ")
        sys.exit(1)


def main():
    print prometheus_url()
    print grafana_url()

if __name__ == '__main__':
    main()
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
    return instances



def get_instance_index(process):
    success = 0.0
    prometheus_instances = get_instances(monitor_params.prometheus_ip, monitor_params.prometheus_port)
    for index in range(len(prometheus_instances)):
        prom_url = 'http://{0}/api/v1/query'.format(prometheus_instances[index])
        param = {
            "query": 'up{{job="{0}"}}'.format(process)
        }
        logging.info("start GET %s?%s", prom_url, param)
        try:
            response = requests.get(prom_url, params=param)
            response.raise_for_status()
        except requests.exceptions.ConnectionError:
            logging.error("GET %s?%s failed! Connection Error.", prom_url, param)
            continue
        except requests.RequestException as e:
            logging.error(e)
            continue
        else:
            logging.info("GET /api/v1/query?%s ok! Response code is = %s", param, response.status_code)
            result = response.json()
            if int(result['data']['result'][0]['value'][1]) == 1:
                success += 1
                return index
            else:
                continue
    if not success:
        logging.error("No prometheus or grafana available, please check it out.")
        sys.exit(1)

def normal_index():
    prom_index = get_instance_index("prometheus")
    grafana_index = get_instance_index("grafana")
    if prom_index == grafana_index:
        logging.info("prometheus and grafana all normal, index is: {0}".format(grafana_index))
        return grafana_index
    elif prom_index < grafana_index:
        ''' prometheus1 ok, but grafana1 down, grafana2 ok.'''
        logging.info("prometheus1 OK, but grafana1 down, using grafana index, the index is: {0}".format(grafana_index))
        return grafana_index
    else:
        ''' prometheus1 down, prometheus2 ok, grafana ok.'''
        logging.info("prometheus1 down, prometheus2 OK. grafana OK, using prometheus index, the index is: {0}".format(prom_index))
        return prom_index

def prometheus_url():
    prometheus_instances = get_instances(monitor_params.prometheus_ip, monitor_params.prometheus_port)
    index = normal_index()
    url = 'http://{0}/api/v1/query'.format(prometheus_instances[index])
    return url

def grafana_url():
    grafana_instances = get_instances(monitor_params.grafana_outside_ip, monitor_params.grafana_port)
    index = normal_index()
    return grafana_instances[index]


def main():
    print prometheus_url()
    print grafana_url()

if __name__ == '__main__':
    main()
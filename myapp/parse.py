#!/usr/bin/env python2
#-*- coding: utf-8 -*-

import requests
import json
import re
import logging
import time
from pprint import pprint
# from util import request_util, dic_to_str, cpu_cores
# from . import params
import params
import base64


# LOG_FILE = 'D:\\Python\\Python_workspace\\log\\parse_json.log'
# logging.basicConfig(filename=LOG_FILE, level=logging.DEBUG)

# filename=cfg.get('log', 'log_path'),
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s',
                    datefmt='%a, %d %b %Y %H:%M:%S')
import sys
logger = logging.getLogger(sys.path[0] + 'parse')

class ParseUtil(object):

    @staticmethod
    def request_metrics(url, param):
        '''
        根据传入的参数，用 requests 库获取 Prometheus 的 metrics 数据
        :param url: 从该 url 抓取数据
        :param param: url + param 拼接成完整的 url，获取数据
        :return: 一组 json 数据
        '''
        data = []

        logging.info("start GET %s?%s", url, param)
        response = requests.get(url, params=param)
        if response.status_code != requests.codes.ok:
            logging.error("GET %s?%s failed! The error code is: %s", url, param, response.status_code)
            return []
        logging.info("GET /api/v1/query?%s ok! Response code is = %s", param, response.status_code)
        results = response.json()
        logger.debug('The results of getting query are: %s', results)
        data = results['data']['result']

        return data



class ScrapeMetrics(object):
    def __init__(self, url, timestamp=time.time(), timeout='2m', **kwargs):
        self._url = url + '/api/v1/query'
        self._timestamp = timestamp
        self._timeout = timeout

    def instances_info(self):
        '''
        去 consul 中获取 instance 的 ip 和 端口，写到一个 json 中，
        :return: a list of strings, like [ 'ip:port', 'ip:port', ... ]
        '''

        ip_list = re.split(r'[,\s]\s*', params.consul_ip)
        consul_port = params.consul_port
        instances = []

        for i in range(len(ip_list)):
            url = 'http://{0}:{1}/v1/catalog/node/node_exporter'.format(ip_list[i], consul_port)
            logging.info("start GET %s", url)
            try:
                response = requests.get(url)
                response.raise_for_status()
            except requests.RequestException as e:
                logging.error(e)
                continue
            else:
                result = response.json()
                pprint(result)
                for value in result['Services'].values():
                    instance = value['Address'] + ':' + str(value['Port'])
                    instances.append(instance)
                break
        pprint(instances)
        return instances

    def cpu_used_ratio(self, instance):
        '''
        calculate the percentage of CPU used, by subtracting the idle usage from 100%:
        100 - (avg by (instance) (irate(node_cpu{job="node",mode="idle"}[5m])) * 100)
        '''
        cpus_used_info = {}
        param = {
            "query": '100-(avg by (instance)(irate(node_cpu{{instance="{0}",mode="idle"}}[5m])) * 100)'.format(instance)
        }
        response = ParseUtil.request_metrics(self._url, param)
        for i in range(len(response)):
            cpus_used_info.setdefault(response[i]['metric']['instance'], response[i]['value'][1])
        pprint(cpus_used_info)
        if cpus_used_info.has_key(instance):
            return cpus_used_info[instance]
        else:
            return []

    def mem_used_ratio(self, instance):
        mem_used_info = {}
        param = {
            "query": '(node_memory_MemTotal{{instance="{0}"}} - node_memory_MemFree{{instance="{0}"}} - node_memory_Cached{{instance="{0}"}}) / (node_memory_MemTotal{{instance="{0}"}}) * 100'.format(instance)
        }
        response = ParseUtil.request_metrics(self._url, param)
        for i in range(len(response)):
            mem_used_info.setdefault(response[i]['metric']['instance'], response[i]['value'][1])
        if mem_used_info.has_key(instance):
            return mem_used_info[instance]
        else:
            return []
        # pprint(response)

    def disk_used_ratio(self, instance):
        disk_used_info = {}
        param = {
            "query": '100 - ((node_filesystem_avail{{instance="{0}",mountpoint="/",fstype!="rootfs"}} * 100) / node_filesystem_size{{instance="{0}",mountpoint="/",fstype!="rootfs"}})'.format(instance)
        }
        response = ParseUtil.request_metrics(self._url, param)
        for i in range(len(response)):
            disk_used_info.setdefault(response[i]['metric']['instance'], response[i]['value'][1])
        if disk_used_info.has_key(instance):
            return disk_used_info[instance]
        else:
            return []


    def host_detail_metrics(self, instance):
        host_info = {
            "href": "{0}/api/v1/hosts/{1}/".format(params.rest_api_url, instance),
            "instance": instance,
            "cpu_used_ratio": self.cpu_used_ratio(instance),
            "disk_used_ratio": self.disk_used_ratio(instance),
            "load": self.host_loads_metrics(instance),
            "memory_used_ratio": self.mem_used_ratio(instance)
        }
        consul_kv_info = self.single_consul_metrics(instance)
        single_host_info = dict(host_info, **consul_kv_info)
        return single_host_info

    def hosts_list_metrics(self):
        hosts_list_info = []
        instance = self.instances_info()
        for i in range(len(instance)):
            hosts_list_info.append(self.host_detail_metrics(instance[i]))
        return hosts_list_info

    def host_loads_metrics(self, instance):
        host_loads_info = {}
        tmp = {}
        param1 = {
            "query": 'node_load1{{instance="{0}"}}'.format(instance)
        }
        response1 = ParseUtil.request_metrics(self._url, param1)
        if len(response1):
            tmp.setdefault("load1",response1[0]['value'][1])
        else:
            tmp.setdefault("load1",[])

        param5 = {
            "query": 'node_load5{{instance="{0}"}}'.format(instance)
        }
        response5 = ParseUtil.request_metrics(self._url, param5)
        if len(response5):
            tmp.setdefault("load5",response5[0]['value'][1])
        else:
            tmp.setdefault("load5",[])

        param15 = {
            "query": 'node_load15{{instance="{0}"}}'.format(instance)
        }
        response15 = ParseUtil.request_metrics(self._url, param15)
        if len(response15):
            tmp.setdefault("load15",response15[0]['value'][1])
        else:
            tmp.setdefault("load15",[])

        host_loads_info.setdefault(instance, tmp)
        pprint(host_loads_info)
        if host_loads_info.has_key(instance):
            return host_loads_info[instance]
        else:
            return []

    def scrape_consul_metrics(self):
        '''
        http://consul_ip:8500/v1/kv/hosts?recurse
        :return: 
        '''
        ip_list = re.split(r'[,\s]\s*', params.consul_ip)
        consul_port = params.consul_port
        consul_info = []

        for i in range(len(ip_list)):
            url = 'http://{0}:{1}/v1/kv/hosts?recurse'.format(ip_list[i], consul_port)
            logging.info("start GET %s", url)
            try:
                response = requests.get(url)
                response.raise_for_status()
            except requests.RequestException as e:
                logging.error(e)
                continue
            else:
                result = response.json()
                for i in range(len(result)):
                    consul_info.append(json.loads(base64.b64decode(result[i]['Value']).decode()))
                break
        logging.debug(consul_info)
        return consul_info

    def single_consul_metrics(self, instance):
        ip = instance.split(":")[0]
        logging.debug('ip = %s', ip)
        consul_metrics = {}

        consul_kv_metrics = self.scrape_consul_metrics()
        for i in range(len(consul_kv_metrics)):
            if consul_kv_metrics[i]['ip'] == ip:
                consul_metrics = consul_kv_metrics[i]
        logging.debug(consul_metrics)
        return consul_metrics


def main():
    url = params.prometheus_url

    h = ScrapeMetrics(url, timestamp=time.time(), timeout='2m')
    h.scrape_consul_metrics()


if __name__ == '__main__':
    main()

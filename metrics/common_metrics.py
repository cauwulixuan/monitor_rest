#!/usr/bin/python
#-*- coding:utf-8 -*-
import os, sys
import re

import requests
import logging
import json

import monitor_params
from time import time
import utils
sys.path.append("..")
from myapp.parse import ParseUtil
from time import time

'''
    Scrape common metrics from Prometheus.
'''

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s',
                    datefmt='%a, %d %b %Y %H:%M:%S')
import sys
logger = logging.getLogger(sys.path[0] + 'common_metrics')

class CommonMetrics(object):

    def __init__(self, name='', **kwargs):
        self._name = name


    def ip_list(self, ip):
        '''
        return common components ip list
        '''
        ip_list = []
        try:
            list = re.split(r'[,\s]\s*', ip.strip())
        except:
            logging.error("Can't split ip {0}. Check the ip in monitor_params.py.".format(ip))
            sys.exit(1)
        else:
            ip_list = list
        return ip_list

    def process_instance(self, ip):
        '''
        @return list of common instances.
        '''
        process_instance = utils.get_instances(ip, monitor_params.process_exporter_port)
        return process_instance
    
    def cluster_state(self, ip):
        '''
        @return cluster state and the numbers of healthy nodes.
        '''
        process_instances = self.process_instance(ip)
        state = 0.0
        success_count = 0.0

        for i in range(len(process_instances)):
            common_up = self.node_state(process_instances[i])
            if common_up:
                success_count +=1
            else:
                continue
        if success_count >= 1:
            state = 1.0
        logging.info("cluster state is %s" % (state))
        return [state, success_count]

    def node_state(self, process_instance):
        '''
        @return a float value 1 or 0, indicating the node state up or down.
        '''
        state = {}
        url = utils.prometheus_url()
        param = {
            "query": '{0}_process_up{{instance="{1}"}}'.format(self._name, process_instance)
        }
        response = ParseUtil.request_metrics(url, param)
        for i in range(len(response)):
            state.setdefault(response[i]['metric']['instance'], response[i]['value'][1])
        if state.has_key(process_instance):
            return float(state[process_instance])
        else:
            logging.error("No instance in the {0} cluster, node {1} down.".format(self._name, process_instance))
            return 0.0


    def cpu_usage(self, process_instance):
        '''
        @return components cpu usage.
        '''
        cpu_usage = {}
        url = utils.prometheus_url()
        param = {
            "query": '{0}_cpu_percentage{{instance="{1}"}}'.format(self._name, process_instance)
        }
        response = ParseUtil.request_metrics(url, param)
        for i in range(len(response)):
            cpu_usage.setdefault(response[i]['metric']['instance'], response[i]['value'][1])
        if cpu_usage.has_key(process_instance):
            return float(cpu_usage[process_instance])
        else:
            logging.error("No instance in the {0} cluster, get {1} cpu usage failed.".format(self._name, process_instance))
            return None

    def uptime(self, process_instance):
        '''
        @return a float value of create time.
        '''
        uptime = {}
        url = utils.prometheus_url()
        param = {
            "query": '{0}_running_time_seconds_total{{instance="{1}"}}'.format(self._name, process_instance)
        }
        response = ParseUtil.request_metrics(url, param)
        for i in range(len(response)):
            uptime.setdefault(response[i]['metric']['instance'], response[i]['value'][1])
        if uptime.has_key(process_instance):
            return float(uptime[process_instance])
        else:
            logging.error("No instance in the {0} cluster, get {1} uptime failed.".format(self._name, process_instance))
            return None

    def mem_usage(self, process_instance):
        '''
        @return components memory usage.
        '''
        mem_usage = {}
        url = utils.prometheus_url()
        param = {
            "query": 'sum by (instance)({0}_memory_usage_bytes_total{{instance="{1}", mode=~"rss|vms|shared"}})'.format(self._name, process_instance)
        }
        response = ParseUtil.request_metrics(url, param)
        for i in range(len(response)):
            mem_usage.setdefault(response[i]['metric']['instance'], response[i]['value'][1])
        if mem_usage.has_key(process_instance):
            return float(mem_usage[process_instance])
        else:
            logging.error("No instance in the {0} cluster, get {1} memory usage failed.".format(self._name, process_instance))
            return None           


    def cluster_list(self, ip):
        process_instances = self.process_instance(ip)
        uptime = time()
        for i in range(len(process_instances)):
            state = self.node_state(process_instances[i])
            if state:
                uptime = self.uptime(process_instances[i])
                break
            else:
                continue

        node_info = []
        for i in range(len(process_instances)):
            node_info.append(self.node_detail(process_instances[i]))

        cluster_info = {
            "{0}_cluster_state".format(self._name) : self.cluster_state(ip)[0],
            "{0}_total_nodes".format(self._name) : float(len(self.ip_list(ip))),
            "{0}_healthy_nodes".format(self._name) : self.cluster_state(ip)[1],
            "{0}_uptime".format(self._name) : time() - uptime,
            "{0}_nodes_info".format(self._name) : node_info
        }
        return cluster_info

    def node_detail(self, process_instance):
        url_name = re.sub('([a-z0-9])_([a-z0-9])', r'\1-\2', self._name).lower()
        if not self.node_state(process_instance):
            node_info = {
                "{0}_node_state".format(self._name) : 0.0,
                "{0}_uptime".format(self._name) : 0.0,
                "{0}_cpu_usage".format(self._name) : 0.0,
                "{0}_mem_usage".format(self._name) : 0.0,
                "{0}_url".format(self._name) : None
            }
        else:
            node_info = {
                "{0}_node_state".format(self._name) : self.node_state(process_instance),
                "{0}_uptime".format(self._name) : time() - self.uptime(process_instance),
                "{0}_cpu_usage".format(self._name) : self.cpu_usage(process_instance),
                "{0}_mem_usage".format(self._name) : self.mem_usage(process_instance),
                "{0}_url".format(self._name) : 'http://{0}/dashboard/db/{1}-dashboard-for-prometheus?orgId=1&var-instance={2}'.format(utils.grafana_url(), url_name, process_instance)
            }
        return node_info

def main():
    prom_name = "prometheus"
    ip = monitor_params.prometheus_ip
    common = CommonMetrics(prom_name)
    from pprint import pprint
    pprint(common.cluster_list(ip))

if __name__ == '__main__':
    main()

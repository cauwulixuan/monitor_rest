#!/usr/bin/python
#-*- coding:utf-8 -*-
import os, sys
import re

import requests
import argparse
import logging
import json

import monitor_params
import utils
sys.path.append('..')
from myapp.parse import ParseUtil
from common_metrics import CommonMetrics
from time import time


'''
    Scrape consul metrics from Consul Cluster or consul_exporter.
'''

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s',
                    datefmt='%a, %d %b %Y %H:%M:%S')
import sys
logger = logging.getLogger(sys.path[0] + 'nginx_metrics')

class GrafanaMetrics(CommonMetrics):

    def __init__(self, name = 'grafana_server'):
        self._name = name

    def instance_info(self, ip):
        instance_list = utils.get_instances(ip, monitor_params.grafana_port)
        return instance_list

    def cluster_list(self, ip):
        process_instances = self.process_instance(ip)
        instances = self.instance_info(ip)
        uptime = time()
        for i in range(len(process_instances)):
            state = self.node_state(process_instances[i])
            if state:
                uptime = self.uptime(process_instances[i])
                break
            else:
                continue

        node_info = []
        for i in range(len(instances)):
            node_info.append(self.grafana_node_detail(process_instances[i], instances[i]))

        cluster_info = {
            "grafana_cluster_state" : self.cluster_state(ip)[0],
            "grafana_total_nodes" : float(len(instances)),
            "grafana_healthy_nodes" : self.cluster_state(ip)[1],
            "grafana_uptime" : time() - uptime,
            "grafana_nodes_info": node_info
        }
        return cluster_info

    def grafana_node_detail(self, process_instance, instance):
        if not self.node_state(process_instance):
            node_info = {
                "grafana_node_state" : 0.0,
                "grafana_uptime" : 0.0,
                "grafana_cpu_usage" : 0.0,
                "grafana_mem_usage" : 0.0,
                "grafana_url" : None
            }
        else:
            node_info = {
                "grafana_node_state" : self.node_state(process_instance),
                "grafana_uptime" : time() - self.uptime(process_instance),
                "grafana_cpu_usage" : self.cpu_usage(process_instance),
                "grafana_mem_usage" : self.mem_usage(process_instance),
                "grafana_url" : 'http://{0}/dashboard/db/grafana-dashboard-for-prometheus?orgId=1&var-instance={1}'.format(utils.grafana_url(), instance)
            }
        return node_info    


def main():
    grafana = GrafanaMetrics()
    
    from pprint import pprint
    pprint(grafana.cluster_list(monitor_params.grafana_ip))


if __name__ == '__main__':
    main()


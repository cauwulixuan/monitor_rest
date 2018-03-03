#!/usr/bin/python
#-*- coding:utf-8 -*-
import os, sys
import re
import time
import requests
import argparse
import logging
import json

import monitor_params
import utils
sys.path.append("..")
from myapp.parse import ParseUtil
from time import time

'''
    Scrape nginx metrics from nginx_exporter.
'''

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s',
                    datefmt='%a, %d %b %Y %H:%M:%S')
import sys
logger = logging.getLogger(sys.path[0] + 'nginx_metrics')

class NginxMetrics(object):

    def __init__(self):
        pass

    def ip_list(self):
        '''
        return nginx_ip list
        '''
        ip_list = []
        try:
            list = re.split(r'[,\s]\s*', monitor_params.nginx_ip.strip())
        except:
            logging.error("Can't split nginx_ip. Check the nginx_ip in monitor_params.py.")
            sys.exit(1)
        else:
            ip_list = list
        return ip_list

    def nginx_cluster_state(self):
        '''
        @return the state of the cluster, including cluster state and healthy nodes in the cluster.
        '''
        process_instances = self.nginx_process_instance()
        state = 0.0
        success_count = 0.0

        for i in range(len(process_instances)):
            nginx_up = self.nginx_node_state(process_instances[i])
            if nginx_up:
                success_count +=1
            else:
                continue
        if success_count >= 1:
            state = 1.0
        logging.info("nginx state is %s" % (state))
        return [state, success_count]
    
    def instance_info(self):
        instance_list = utils.get_instances(monitor_params.nginx_ip, monitor_params.nginx_exporter_port)
        return instance_list

    def nginx_process_instance(self):
        '''
        @return list of nginx instances.
        '''
        process_instances = utils.get_instances(monitor_params.nginx_ip, monitor_params.process_exporter_port)
        return process_instances
    
    def nginx_node_state(self, process_instance):
        '''
        @return a float value 1 or 0, indicating the node state up or down.
        '''
        state = {}
        url = utils.prometheus_url()
        param = {
            "query": 'nginx_process_up{{instance="{0}"}}'.format(process_instance)
        }
        response = ParseUtil.request_metrics(url, param)
        for i in range(len(response)):
            state.setdefault(response[i]['metric']['instance'], response[i]['value'][1])
        if state.has_key(process_instance):
            print float(state[process_instance])
            return float(state[process_instance])
        else:
            logging.error("No instance in the nginx cluster, nginx node {0} down.".format(process_instance))
            return 0.0


    def nginx_cpu_usage(self, process_instance):
        '''
        @return a float value 1 or 0, indicating the node state up or down.
        '''
        cpu_usage = {}
        url = utils.prometheus_url()
        param = {
            "query": 'nginx_cpu_percentage{{instance="{0}"}}'.format(process_instance)
        }
        response = ParseUtil.request_metrics(url, param)
        # pprint(response)
        for i in range(len(response)):
            cpu_usage.setdefault(response[i]['metric']['instance'], response[i]['value'][1])
        if cpu_usage.has_key(process_instance):
            print float(cpu_usage[process_instance])
            return float(cpu_usage[process_instance])
        else:
            logging.error("No instance in the nginx cluster, get {0} cpu usage error.".format(process_instance))
            return None

    def nginx_uptime(self, process_instance):
        '''
        @return a float value 1 or 0, indicating the node state up or down.
        '''
        uptime = {}
        url = utils.prometheus_url()
        param = {
            "query": 'nginx_running_time_seconds_total{{instance="{0}"}}'.format(process_instance)
        }
        response = ParseUtil.request_metrics(url, param)
        # pprint(response)
        for i in range(len(response)):
            uptime.setdefault(response[i]['metric']['instance'], response[i]['value'][1])
        if uptime.has_key(process_instance):
            print float(uptime[process_instance])
            return float(uptime[process_instance])
        else:
            logging.error("No instance in the nginx cluster, get {0} uptime error.".format(process_instance))
            return None

    def nginx_mem_usage(self, process_instance):
        '''
        @return a float value 1 or 0, indicating the node state up or down.
        '''
        mem_usage = {}
        url = utils.prometheus_url()
        param = {
            "query": 'sum by (instance)(nginx_memory_usage_bytes_total{{instance="{0}", mode=~"rss|vms|shared"}})'.format(process_instance)
        }
        response = ParseUtil.request_metrics(url, param)
        # pprint(response)
        for i in range(len(response)):
            mem_usage.setdefault(response[i]['metric']['instance'], response[i]['value'][1])
        if mem_usage.has_key(process_instance):
            print float(mem_usage[process_instance])
            return float(mem_usage[process_instance])
        else:
            logging.error("No instance in the nginx cluster, get {0} memory usage error.".format(process_instance))
            return None           


    def nginx_cluster_list(self):
        process_instances = self.nginx_process_instance()
        instances = self.instance_info()
        uptime = time()
        for i in range(len(process_instances)):
            state = self.nginx_node_state(process_instances[i])
            if state:
                uptime = self.nginx_uptime(process_instances[i])
                break
            else:
                continue

        node_info = []
        for i in range(len(instances)):
            node_info.append(self.nginx_node_detail(process_instances[i], instances[i]))

        cluster_info = {
            "nginx_cluster_state" : self.nginx_cluster_state()[0],
            "nginx_total_nodes" : float(len(self.ip_list())),
            "nginx_healthy_nodes" : self.nginx_cluster_state()[1],
            "nginx_uptime" : time() - uptime,
            "nginx_nodes_info": node_info
        }
        # pprint(cluster_info)
        return cluster_info

    def nginx_node_detail(self, process_instance, instance):
        '''
        For this time, I didn't install nginx_exporter or nginxlog_exporter, so in nginx_url only process_instance in use.
        '''
        if not self.nginx_node_state(process_instance):
            node_info = {
                "nginx_node_state" : 0.0,
                "nginx_uptime" : 0.0,
                "nginx_cpu_usage" : 0.0,
                "nginx_mem_usage" : 0.0,
                "nginx_url" : None
            }
        else:
            node_info = {
                "nginx_node_state" : self.nginx_node_state(process_instance),
                "nginx_uptime" : time() - self.nginx_uptime(process_instance),
                "nginx_cpu_usage" : self.nginx_cpu_usage(process_instance),
                "nginx_mem_usage" : self.nginx_mem_usage(process_instance),
                "nginx_url" : 'http://{0}/dashboard/db/nginx-dashboard-for-prometheus?orgId=1&var-instance={1}'.format(utils.grafana_url(), process_instance)
            }
        return node_info

def main():
    nginx = NginxMetrics()
    nginx.nginx_cluster_list()


if __name__ == '__main__':
    main()

#!/usr/bin/python
#-*- coding:utf-8 -*-
import os, sys
import re

import requests
import argparse
import logging
import json

import monitor_params
from time import time
import utils
sys.path.append("..")
from myapp.parse import ParseUtil
from time import time


'''
    Scrape prometheus metrics from Prometheus.
'''

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s',
                    datefmt='%a, %d %b %Y %H:%M:%S')
import sys
logger = logging.getLogger(sys.path[0] + 'nginx_metrics')

class PrometheusMetrics(object):

    def __init__(self):
        pass


    def ip_list(self):
        '''
        return tomcat_ip list
        '''
        ip_list = []
        try:
            list = re.split(r'[,\s]\s*', monitor_params.prometheus_ip.strip())
        except:
            logging.error("Can't split prometheus_ip. Check the prometheus_ip in monitor_params.py.")
            sys.exit(1)
        else:
            ip_list = list
        
        print ip_list
        return ip_list 

    def instance_info(self):
        '''
        @return prometheus instance.
        '''
        instance_list = utils.get_instances(monitor_params.prometheus_ip, monitor_params.prometheus_port)
        return instance_list

    def prometheus_process_instance(self):
        '''
        @return a list of prometheus process instances.
        '''
        process_instance = utils.get_instances(monitor_params.prometheus_ip, monitor_params.process_exporter_port)
        return process_instance
    
    def prometheus_cluster_state(self):
        '''
        @return prometheus cluster state and numbers of healthy nodes.
        '''
        process_instances = self.prometheus_process_instance()
        state = 0.0
        success_count = 0.0

        for i in range(len(process_instances)):
            prometheus_up = self.prometheus_node_state(process_instances[i])
            if prometheus_up:
                success_count +=1
            else:
                continue
        if success_count >= 1:
            state = 1.0
        logging.debug("prometheus state is %s" % (state))
        return [state, success_count]

    def prometheus_node_state(self, process_instance):
        '''
        @return a float value 1 or 0, indicating the node state up or down.
        '''
        state = {}
        url = utils.prometheus_url()
        param = {
            "query": 'prometheus_process_up{{instance="{0}"}}'.format(process_instance)
        }
        response = ParseUtil.request_metrics(url, param)
        for i in range(len(response)):
            state.setdefault(response[i]['metric']['instance'], response[i]['value'][1])
        if state.has_key(process_instance):
            print float(state[process_instance])
            return float(state[process_instance])
        else:
            logging.error("No instance in the prometheus cluster, prometheus node {0} down.".format(process_instance))
            return 0.0


    def prometheus_cpu_usage(self, process_instance):
        '''
        @return process_instance cpu usage.
        '''
        cpu_usage = {}
        url = utils.prometheus_url()
        param = {
            "query": 'prometheus_cpu_percentage{{instance="{0}"}}'.format(process_instance)
        }
        response = ParseUtil.request_metrics(url, param)
        for i in range(len(response)):
            cpu_usage.setdefault(response[i]['metric']['instance'], response[i]['value'][1])
        if cpu_usage.has_key(process_instance):
            print float(cpu_usage[process_instance])
            return float(cpu_usage[process_instance])
        else:
            logging.error("No instance in the prometheus cluster, get prometheus node {0} cpu usage failed.".format(process_instance))
            return None

    def prometheus_uptime(self, process_instance):
        '''
        @return process_instance create time.
        '''
        uptime = {}
        url = utils.prometheus_url()
        param = {
            "query": 'prometheus_running_time_seconds_total{{instance="{0}"}}'.format(process_instance)
        }
        response = ParseUtil.request_metrics(url, param)
        for i in range(len(response)):
            uptime.setdefault(response[i]['metric']['instance'], response[i]['value'][1])
        if uptime.has_key(process_instance):
            print float(uptime[process_instance])
            return float(uptime[process_instance])
        else:
            logging.error("No instance in the prometheus cluster, get prometheus node {0} uptime failed.".format(process_instance))
            return None

    def prometheus_mem_usage(self, process_instance):
        '''
        @return process_instance memory usage.
        '''
        mem_usage = {}
        url = utils.prometheus_url()
        param = {
            "query": 'sum by (instance)(prometheus_memory_usage_bytes_total{{instance="{0}", mode=~"rss|vms|shared"}})'.format(process_instance)
        }
        response = ParseUtil.request_metrics(url, param)
        for i in range(len(response)):
            mem_usage.setdefault(response[i]['metric']['instance'], response[i]['value'][1])
        if mem_usage.has_key(process_instance):
            print float(mem_usage[process_instance])
            return float(mem_usage[process_instance])
        else:
            logging.error("No instance in the prometheus cluster, get prometheus node {0} memory usage failed.".format(process_instance))
            return None           


    def prometheus_cluster_list(self):
        process_instances = self.prometheus_process_instance()
        grafana_instances = self.grafana_instance()
        uptime = time()
        for i in range(len(process_instances)):
            state = self.prometheus_node_state(process_instances[i])
            if state:
                uptime = self.prometheus_uptime(process_instances[i])
                break
            else:
                continue

        node_info = []
        for i in range(len(process_instances)):
            node_info.append(self.prometheus_node_detail(process_instances[i], grafana_instances[i]))

        cluster_info = {
            "prometheus_cluster_state" : self.prometheus_cluster_state()[0],
            "prometheus_total_nodes" : float(len(self.ip_list())),
            "prometheus_healthy_nodes" : self.prometheus_cluster_state()[1],
            "prometheus_uptime" : time() - uptime,
            "prometheus_nodes_info": node_info
        }
        return cluster_info
    
    def grafana_instance(self):
        instance_list = utils.get_instances(monitor_params.grafana_outside_ip, monitor_params.grafana_port)
        return instance_list

    def prometheus_node_detail(self, process_instance, grafana_instance):
        if not self.prometheus_node_state(process_instance):
            node_info = {
                "prometheus_node_state" : 0.0,
                "prometheus_uptime" : 0.0,
                "prometheus_cpu_usage" : 0.0,
                "prometheus_mem_usage" : 0.0,
                "prometheus_url" : None
            }
        else:
            node_info = {
                "prometheus_node_state" : self.prometheus_node_state(process_instance),
                "prometheus_uptime" : time() - self.prometheus_uptime(process_instance),
                "prometheus_cpu_usage" : self.prometheus_cpu_usage(process_instance),
                "prometheus_mem_usage" : self.prometheus_mem_usage(process_instance),
                "prometheus_url" : 'http://{0}/dashboard/db/prometheus-stats?orgId=1'.format(grafana_instance)
            }
        return node_info


def main():
    prometheus = PrometheusMetrics()
    prometheus.prometheus_cluster_list()


if __name__ == '__main__':
    main()


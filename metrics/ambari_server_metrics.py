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
    Scrape ambari_server metrics from Prometheus.
'''

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s',
                    datefmt='%a, %d %b %Y %H:%M:%S')
import sys
logger = logging.getLogger(sys.path[0] + 'nginx_metrics')

class AmbariServerMetrics(object):

    def __init__(self):
        pass


    def ip_list(self):
        '''
        return tomcat_ip list
        '''
        ip_list = []
        try:
            list = re.split(r'[,\s]\s*', monitor_params.ambari_server_ip.strip())
        except:
            logging.error("Can't split ambari_server_ip. Check the ambari_server_ip in monitor_params.py.")
            sys.exit(1)
        else:
            ip_list = list
        return ip_list

    def ambari_server_process_instance(self):
        '''
        @return list of ambari_server instances.
        '''
        process_instance = utils.get_instances(monitor_params.ambari_server_ip, monitor_params.process_exporter_port)
        logging.info("Ambari-server PROCESS INSTANCE: {0}".format(process_instance))
        return process_instance
    
    def ambari_server_cluster_state(self):
        '''
        @return ambari-servers state and numbers of healthy nodes.
        '''
        process_instances = self.ambari_server_process_instance()
        state = 0.0
        success_count = 0.0

        for i in range(len(process_instances)):
            ambari_server_up = self.ambari_server_node_state(process_instances[i])
            if ambari_server_up:
                success_count +=1
            else:
                continue
        if success_count >= 1:
            state = 1.0
        logging.info("ambari_server state is %s" % (state))
        return [state, success_count]

    def ambari_server_node_state(self, process_instance):
        '''
        @return a float value 1 or 0, indicating the node state up or down.
        '''
        state = {}
        url = utils.prometheus_url()
        param = {
            "query": 'ambari_server_process_up{{instance="{0}"}}'.format(process_instance)
        }
        response = ParseUtil.request_metrics(url, param)
        for i in range(len(response)):
            state.setdefault(response[i]['metric']['instance'], response[i]['value'][1])
        if state.has_key(process_instance):
            return float(state[process_instance])
        else:
            logging.error("No instance in the ambari-server cluster, ambari-server {0} down.".format(process_instance))
            return 0.0


    def ambari_server_cpu_usage(self, process_instance):
        '''
        @return ambari-server cpu usage.
        '''
        cpu_usage = {}
        url = utils.prometheus_url()
        param = {
            "query": 'ambari_server_cpu_percentage{{instance="{0}"}}'.format(process_instance)
        }
        response = ParseUtil.request_metrics(url, param)
        for i in range(len(response)):
            cpu_usage.setdefault(response[i]['metric']['instance'], response[i]['value'][1])
        if cpu_usage.has_key(process_instance):
            return float(cpu_usage[process_instance])
        else:
            logging.error("No instance in the ambari-server cluster, get ambari-server {0} cpu usage failed.".format(process_instance))
            return None

    def ambari_server_uptime(self, process_instance):
        '''
        @return a float value of create time.
        '''
        uptime = {}
        url = utils.prometheus_url()
        param = {
            "query": 'ambari_server_running_time_seconds_total{{instance="{0}"}}'.format(process_instance)
        }
        response = ParseUtil.request_metrics(url, param)
        for i in range(len(response)):
            uptime.setdefault(response[i]['metric']['instance'], response[i]['value'][1])
        if uptime.has_key(process_instance):
            return float(uptime[process_instance])
        else:
            logging.error("No instance in the ambari-server cluster, get ambari-server {0} uptime failed.".format(process_instance))
            return None

    def ambari_server_mem_usage(self, process_instance):
        '''
        @return ambari-server memory usage.
        '''
        mem_usage = {}
        url = utils.prometheus_url()
        param = {
            "query": 'sum by (instance)(ambari_server_memory_usage_bytes_total{{instance="{0}", mode=~"rss|vms|shared"}})'.format(process_instance)
        }
        response = ParseUtil.request_metrics(url, param)
        for i in range(len(response)):
            mem_usage.setdefault(response[i]['metric']['instance'], response[i]['value'][1])
        if mem_usage.has_key(process_instance):
            return float(mem_usage[process_instance])
        else:
            logging.error("No instance in the ambari-server cluster, get ambari-server {0} memory usage failed.".format(process_instance))
            return None           

    def ambari_server_cluster_list(self):
        process_instances = self.ambari_server_process_instance()
        uptime = time()
        for i in range(len(process_instances)):
            state = self.ambari_server_node_state(process_instances[i])
            if state:
                uptime = self.ambari_server_uptime(process_instances[i])
                break
            else:
                continue

        node_info = []
        for i in range(len(process_instances)):
            node_info.append(self.ambari_server_node_detail(process_instances[i]))

        cluster_info = {
            "ambari_server_cluster_state" : self.ambari_server_cluster_state()[0],
            "ambari_server_total_nodes" : float(len(self.ip_list())),
            "ambari_server_healthy_nodes" : self.ambari_server_cluster_state()[1],
            "ambari_server_uptime" : time() - uptime,
            "ambari_server_nodes_info": node_info
        }
        return cluster_info

    def ambari_server_node_detail(self, process_instance):
        logging.info("STATE IS : {0}".format(self.ambari_server_node_state(process_instance)))
        if not self.ambari_server_node_state(process_instance):
            node_info = {
                "ambari_server_node_state" : 0.0,
                "ambari_server_uptime" : 0.0,
                "ambari_server_cpu_usage" : 0.0,
                "ambari_server_mem_usage" : 0.0,
                "prometheus_url" : None
            }
        else:
            node_info = {
                "ambari_server_node_state" : self.ambari_server_node_state(process_instance),
                "ambari_server_uptime" : time() - self.ambari_server_uptime(process_instance),
                "ambari_server_cpu_usage" : self.ambari_server_cpu_usage(process_instance),
                "ambari_server_mem_usage" : self.ambari_server_mem_usage(process_instance),
                "ambari_server_url" : 'http://{0}/dashboard/db/ambari-server-dashboard-for-prometheus?orgId=1&var-instance={1}'.format(utils.grafana_url(), process_instance)
            }
        return node_info


def main():
    ambari_server = AmbariServerMetrics()
    ambari_server.ambari_server_cluster_list()

if __name__ == '__main__':
    main()


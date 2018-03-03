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
from time import time


'''
    Scrape consul metrics from Consul Cluster or consul_exporter.
'''

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s',
                    datefmt='%a, %d %b %Y %H:%M:%S')
import sys
logger = logging.getLogger(sys.path[0] + 'nginx_metrics')

class GrafanaMetrics(object):

    def __init__(self):
        pass


    def ip_list(self):
        '''
        return grafana_ip list
        '''
        ip_list = []
        try:
            list = re.split(r'[,\s]\s*', monitor_params.grafana_ip)
        except:
            logging.error("Can't split grafana_ip. Check the grafana_exporter_ip in monitor_params.py.")
            sys.exit(1)
        else:
            ip_list = list
        
        print ip_list
        return ip_list


    def instance_info(self):
        instance_list = utils.get_instances(monitor_params.grafana_ip, monitor_params.grafana_port)
        return instance_list

    def grafana_process_instance(self):
        '''
        @return list of grafana process instances.
        '''
        process_instance = utils.get_instances(monitor_params.grafana_ip, monitor_params.process_exporter_port)
        return process_instance
    
    def grafana_cluster_state(self):
        '''
        @return grafana cluster state, and numbers of healthy nodes.
        '''
        process_instances = self.grafana_process_instance()
        state = 0.0
        success_count = 0.0

        for i in range(len(process_instances)):
            grafana_up = self.grafana_node_state(process_instances[i])
            if grafana_up:
                success_count +=1
            else:
                continue
        if success_count >= 1:
            state = 1.0
        logging.debug("grafana state is %s" % (state))
        return [state, success_count]

    def grafana_node_state(self, process_instance):
        '''
        @return a float value 1 or 0, indicating the node state up or down.
        '''
        state = {}
        url = utils.prometheus_url()
        param = {
            "query": 'grafana_server_process_up{{instance="{0}"}}'.format(process_instance)
        }
        response = ParseUtil.request_metrics(url, param)
        for i in range(len(response)):
            state.setdefault(response[i]['metric']['instance'], response[i]['value'][1])
        if state.has_key(process_instance):
            print float(state[process_instance])
            return float(state[process_instance])
        else:
            logging.error("No instance in the grafana cluster, grafana {0} down.".format(process_instance))
            return 0.0


    def grafana_cpu_usage(self, process_instance):
        '''
        @return process_instance cpu usage.
        '''
        cpu_usage = {}
        url = utils.prometheus_url()
        param = {
            "query": 'grafana_server_cpu_percentage{{instance="{0}"}}'.format(process_instance)
        }
        response = ParseUtil.request_metrics(url, param)
        for i in range(len(response)):
            cpu_usage.setdefault(response[i]['metric']['instance'], response[i]['value'][1])
        if cpu_usage.has_key(process_instance):
            print float(cpu_usage[process_instance])
            return float(cpu_usage[process_instance])
        else:
            logging.error("No instance in the grafana cluster, get grafana {0} cpu usage failed.".format(process_instance))
            return None

    def grafana_uptime(self, process_instance):
        '''
        @return process_instance create time.
        '''
        uptime = {}
        url = utils.prometheus_url()
        param = {
            "query": 'grafana_server_running_time_seconds_total{{instance="{0}"}}'.format(process_instance)
        }
        response = ParseUtil.request_metrics(url, param)
        for i in range(len(response)):
            uptime.setdefault(response[i]['metric']['instance'], response[i]['value'][1])
        if uptime.has_key(process_instance):
            print float(uptime[process_instance])
            return float(uptime[process_instance])
        else:
            logging.error("No instance in the grafana cluster, get grafana {0} uptime failed.".format(process_instance))
            return None

    def grafana_mem_usage(self, process_instance):
        '''
        @return process_instance memory usage.
        '''
        mem_usage = {}
        url = utils.prometheus_url()
        param = {
            "query": 'sum by (instance)(grafana_server_memory_usage_bytes_total{{instance="{0}", mode=~"rss|vms|shared"}})'.format(process_instance)
        }
        response = ParseUtil.request_metrics(url, param)
        for i in range(len(response)):
            mem_usage.setdefault(response[i]['metric']['instance'], response[i]['value'][1])
        if mem_usage.has_key(process_instance):
            print float(mem_usage[process_instance])
            return float(mem_usage[process_instance])
        else:
            logging.error("No instance in the grafana cluster, get grafana {0} memory usage failed.".format(process_instance))
            return None           

    def grafana_outside_instance(self):
        '''
        For outside access, the url must use a grafana_outside_ip
        '''
        outside_instances = utils.get_instances(monitor_params.grafana_outside_ip, monitor_params.grafana_port)
        return outside_instances

    def grafana_cluster_list(self):
        process_instances = self.grafana_process_instance()
        outside_instances = self.grafana_outside_instance()
        instances = self.instance_info()
        uptime = time()
        for i in range(len(process_instances)):
            state = self.grafana_node_state(process_instances[i])
            if state:
                uptime = self.grafana_uptime(process_instances[i])
                break
            else:
                continue

        node_info = []
        for i in range(len(instances)):
            node_info.append(self.grafana_node_detail(process_instances[i], outside_instances[i], instances[i]))

        cluster_info = {
            "grafana_cluster_state" : self.grafana_cluster_state()[0],
            "grafana_total_nodes" : float(len(self.ip_list())),
            "grafana_healthy_nodes" : self.grafana_cluster_state()[1],
            "grafana_uptime" : time() - uptime,
            "grafana_nodes_info": node_info
        }
        return cluster_info

    def grafana_node_detail(self, process_instance, outside_instance, instance):
        if not self.grafana_node_state(process_instance):
            node_info = {
                "grafana_node_state" : 0.0,
                "grafana_uptime" : 0.0,
                "grafana_cpu_usage" : 0.0,
                "grafana_mem_usage" : 0.0,
                "grafana_url" : None
            }
        else:
            node_info = {
                "grafana_node_state" : self.grafana_node_state(process_instance),
                "grafana_uptime" : time() - self.grafana_uptime(process_instance),
                "grafana_cpu_usage" : self.grafana_cpu_usage(process_instance),
                "grafana_mem_usage" : self.grafana_mem_usage(process_instance),
                "grafana_url" : 'http://{0}/dashboard/db/grafana-dashboard-for-prometheus?orgId=1&var-instance={1}'.format(outside_instance, instance)
            }
        return node_info    


def main():
    grafana = GrafanaMetrics()
    grafana.grafana_cluster_list()


if __name__ == '__main__':
    main()


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
from common_metrics import CommonMetrics
from time import time


'''
    Scrape tomcat metrics from tomcat_exporter.
'''

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s',
                    datefmt='%a, %d %b %Y %H:%M:%S')
import sys
logger = logging.getLogger(sys.path[0] + 'tomcat_metrics')

class TomcatMetrics(CommonMetrics):

    def __init__(self, name = 'tomcat'):
        self.master_name = "{0}_master".format(name)
        self.tenant_name = "{0}_tenant".format(name)
    
    def master_instance(self):
        '''
        @return tomcat instance, include tomcat_ip:master_port
        '''
        master_instance = utils.get_instances(monitor_params.tomcat_ip, monitor_params.tomcat_master_port)
        return master_instance

    def tenant_instance(self):
        '''
        @return tomcat instance, include tomcat_ip:tenant_port
        '''
        tenant_instance = utils.get_instances(monitor_params.tomcat_ip, monitor_params.tomcat_tenant_port)
        return tenant_instance

    def tomcat_node_state(self, role, process_instance):
        '''
        @return a float value 1 or 0, indicating the node state up or down.
        '''
        state = {}
        url = utils.prometheus_url()
        param = {
            "query": '{0}_process_up{{instance="{1}"}}'.format(role, process_instance)
        }
        response = ParseUtil.request_metrics(url, param)
        for i in range(len(response)):
            state.setdefault(response[i]['metric']['instance'], response[i]['value'][1])
        if state.has_key(process_instance):
            return float(state[process_instance])
        else:
            logging.error("No instance in the tomcat cluster, tomcat {0} node {1} down.".format(role, process_instance))
            return 0.0

    def cluster_state(self, ip):
        '''
        @return tomcat cluster state, and the numbers of healthy nodes.
        '''
        master_instances = self.master_instance()
        tenant_instances = self.tenant_instance()
        process_instances = self.process_instance(ip)
        state = 0.0
        success_count = 0.0
        master_count = 0.0
        tenant_count = 0.0

        for i in range(len(process_instances)):
            master_up = self.tomcat_node_state(self.master_name, process_instances[i])
            tenant_up = self.tomcat_node_state(self.tenant_name, process_instances[i])
            if master_up:
                master_count += 1
            if tenant_up:
                tenant_count += 1
        success_count = master_count + tenant_count
        if master_count >= 1 and tenant_count >=1:
            state = 1.0
        logging.info("tomcat state is %s" % (state))
        return [state, success_count]

    def tomcat_cpu_usage(self, role, process_instance):
        '''
        @return a float value 1 or 0, indicating the node state up or down.
        '''
        cpu_usage = {}
        url = utils.prometheus_url()
        param = {
            "query": '{0}_cpu_percentage{{instance="{1}"}}'.format(role, process_instance)
        }
        response = ParseUtil.request_metrics(url, param)
        for i in range(len(response)):
            cpu_usage.setdefault(response[i]['metric']['instance'], response[i]['value'][1])
        if cpu_usage.has_key(process_instance):
            print float(cpu_usage[process_instance])
            return float(cpu_usage[process_instance])
        else:
            logging.error("No instance in the tomcat cluster, get tomcat {0} node {1} cpu usage failed.".format(role, process_instance))
            return None

    def tomcat_uptime(self, role, process_instance):
        '''
        @return a float value 1 or 0, indicating the node state up or down.
        '''
        uptime = {}
        url = utils.prometheus_url()
        param = {
            "query": '{0}_running_time_seconds_total{{instance="{1}"}}'.format(role, process_instance)
        }
        response = ParseUtil.request_metrics(url, param)
        for i in range(len(response)):
            uptime.setdefault(response[i]['metric']['instance'], response[i]['value'][1])
        if uptime.has_key(process_instance):
            return float(uptime[process_instance])
        else:
            logging.error("No instance in the tomcat cluster, get tomcat {0} node {1} uptime failed.".format(role, process_instance))
            return None

    def tomcat_mem_usage(self, role, process_instance):
        '''
        @return a float value 1 or 0, indicating the node state up or down.
        '''
        mem_usage = {}
        url = utils.prometheus_url()
        param = {
            "query": 'sum by (instance)({0}_memory_usage_bytes_total{{instance="{1}", mode=~"rss|vms|shared"}})'.format(role, process_instance)
        }
        response = ParseUtil.request_metrics(url, param)
        for i in range(len(response)):
            mem_usage.setdefault(response[i]['metric']['instance'], response[i]['value'][1])
        if mem_usage.has_key(process_instance):
            return float(mem_usage[process_instance])
        else:
            logging.error("No instance in the tomcat cluster, get tomcat {0} node {1} memory usage failed.".format(role, process_instance))
            return None           

    def cluster_list(self, ip):
        master_instances = self.master_instance()
        tenant_instances = self.tenant_instance()
        process_instances = self.process_instance(ip)
        uptime = time()
        for i in range(len(process_instances)):
            master_state = self.tomcat_node_state(self.master_name, process_instances[i])
            tenant_state = self.tomcat_node_state(self.tenant_name, process_instances[i])
            if master_state:
                uptime = self.tomcat_uptime(self.master_name, process_instances[i])
                break
            elif tenant_state:
                uptime = self.tomcat_uptime(self.tenant_name, process_instances[i])
                break
            else:
                continue

        master_info = []
        tenant_info = []
        for i in range(len(master_instances)):
            master_info.append(self.tomcat_node_detail(self.master_name, process_instances[i], master_instances[i]))
            tenant_info.append(self.tomcat_node_detail(self.tenant_name, process_instances[i], tenant_instances[i]))

        cluster_info = {
            "tomcat_cluster_state" : self.cluster_state(ip)[0],
            "tomcat_total_nodes" : float(sum([len(master_instances), len(tenant_instances)])),
            "tomcat_healthy_nodes" : self.cluster_state(ip)[1],
            "tomcat_uptime" : time() - uptime,
            "tomcat_master_info": master_info,
            "tomcat_tenant_info": tenant_info
        }
        return cluster_info

    def tomcat_node_detail(self, role, process_instance, role_instance):
        if not self.tomcat_node_state(role, process_instance):
            node_info = {
                "tomcat_{0}_state".format(role) : 0.0,
                "tomcat_{0}_uptime".format(role) : 0.0,
                "tomcat_{0}_cpu_usage".format(role) : 0.0,
                "tomcat_{0}_mem_usage".format(role) : 0.0,
                "tomcat_{0}_url".format(role) : None
            }
        else:
            node_info = {
                "tomcat_{0}_node_state".format(role) : self.tomcat_node_state(role, process_instance),
                "tomcat_{0}_uptime".format(role) : time() - self.tomcat_uptime(role, process_instance),
                "tomcat_{0}_cpu_usage".format(role) : self.tomcat_cpu_usage(role, process_instance),
                "tomcat_{0}_mem_usage".format(role) : self.tomcat_mem_usage(role, process_instance),
                "tomcat_{0}_url".format(role) : 'http://{0}/dashboard/db/tomcat-dashboard-for-prometheus?orgId=1&var-instance={1}'.format(utils.grafana_url(), role_instance)
            }
        return node_info

def main():
    tomcat = TomcatMetrics()
    from pprint import pprint
    pprint(tomcat.cluster_list(monitor_params.tomcat_ip))

if __name__ == '__main__':
    main()


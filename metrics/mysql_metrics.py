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

'''
    Scrape mysqld metrics from mysqld_exporter.
'''

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s',
                    datefmt='%a, %d %b %Y %H:%M:%S')
import sys
logger = logging.getLogger(sys.path[0] + 'mysql_metrics')

class MysqlMetrics(object):

    def __init__(self):
        pass


    def ip_list(self):
        '''
        return mysql_ip list
        '''
        ip_list = []
        try:
            list = re.split(r'[,\s]\s*', monitor_params.mysql_ip.strip())
        except:
            logging.error("Can't split mysql_ip. Check the mysql_ip in monitor_params.py.")
            sys.exit(1)
        else:
            ip_list = list
        return ip_list

    def instance_info(self):
        '''
        @return a list of mysqld_exporter instances.
        '''
        instance_list = utils.get_instances(monitor_params.mysql_ip, monitor_params.mysql_exporter_port)
        return instance_list

    def mysql_process_instance(self):
        '''
        @return list of mysql process instances.
        '''
        process_instance = utils.get_instances(monitor_params.mysql_ip, monitor_params.process_exporter_port)
        return process_instance
    
    def mysql_cluster_state(self):
        '''
        @return mysql cluster state and the numbers of healthy nodes.
        '''
        process_instances = self.mysql_process_instance()
        state = 0.0
        success_count = 0.0

        for i in range(len(process_instances)):
            mysql_up = self.mysql_node_state(process_instances[i])
            if mysql_up:
                success_count +=1
            else:
                continue
        if success_count == len(process_instances):
            state = 1.0
        logging.info("mysql state is %s" % (state))
        return [state, success_count]

    def mysql_node_state(self, process_instance):
        '''
        @return a float value 1 or 0, indicating the node state up or down.
        '''
        state = {}
        url = utils.prometheus_url()
        param = {
            "query": 'mysqld_process_up{{instance="{0}"}}'.format(process_instance)
        }
        response = ParseUtil.request_metrics(url, param)
        for i in range(len(response)):
            state.setdefault(response[i]['metric']['instance'], response[i]['value'][1])
        if state.has_key(process_instance):
            print float(state[process_instance])
            return float(state[process_instance])
        else:
            logging.error("No instance in the mysql cluster, mysql node {0} down.".format(process_instance))
            return 0.0

    def mysql_cpu_usage(self, process_instance):
        '''
        @return a float value 1 or 0, indicating the node state up or down.
        '''
        cpu_usage = {}
        url = utils.prometheus_url()
        param = {
            "query": 'mysqld_cpu_percentage{{instance="{0}"}}'.format(process_instance)
        }
        response = ParseUtil.request_metrics(url, param)
        # pprint(response)
        for i in range(len(response)):
            cpu_usage.setdefault(response[i]['metric']['instance'], response[i]['value'][1])
        if cpu_usage.has_key(process_instance):
            print float(cpu_usage[process_instance])
            return float(cpu_usage[process_instance])
        else:
            logging.error("No instance in the mysql cluster, get mysql node {0} cpu usage failed.".format(process_instance))
            return None

    def mysql_uptime(self, process_instance):
        '''
        @return a float value of create time, indicating the node state up or down.
        '''
        uptime = {}
        url = utils.prometheus_url()
        param = {
            "query": 'mysqld_running_time_seconds_total{{instance="{0}"}}'.format(process_instance)
        }
        response = ParseUtil.request_metrics(url, param)
        for i in range(len(response)):
            uptime.setdefault(response[i]['metric']['instance'], response[i]['value'][1])
        if uptime.has_key(process_instance):
            print float(uptime[process_instance])
            return float(uptime[process_instance])
        else:
            logging.error("No instance in the mysql cluster, get mysql node {0} uptime failed.".format(process_instance))
            return None

    def mysql_mem_usage(self, process_instance):
        '''
        @return a float value 1 or 0, indicating the node state up or down.
        '''
        mem_usage = {}
        url = utils.prometheus_url()
        param = {
            "query": 'sum by (instance)(mysqld_memory_usage_bytes_total{{instance="{0}", mode=~"rss|vms|shared"}})'.format(process_instance)
        }
        response = ParseUtil.request_metrics(url, param)
        for i in range(len(response)):
            mem_usage.setdefault(response[i]['metric']['instance'], response[i]['value'][1])
        if mem_usage.has_key(process_instance):
            print float(mem_usage[process_instance])
            return float(mem_usage[process_instance])
        else:
            logging.error("No instance in the mysql cluster, get mysql node {0} memory usage failed.".format(process_instance))
            return None           


    def mysql_cluster_list(self):
        process_instances = self.mysql_process_instance()
        instances = self.instance_info()
        uptime = time()
        for i in range(len(process_instances)):
            state = self.mysql_node_state(process_instances[i])
            if state:
                uptime = self.mysql_uptime(process_instances[i])
                break
            else:
                continue

        node_info = []
        for i in range(len(instances)):
            node_info.append(self.mysql_node_detail(process_instances[i], instances[i]))

        cluster_info = {
            "mysql_cluster_state" : self.mysql_cluster_state()[0],
            "mysql_total_nodes" : float(len(process_instances)),
            "mysql_healthy_nodes" : self.mysql_cluster_state()[1],
            "mysql_uptime" : time() - uptime,
            "mysql_nodes_info": node_info
        }
        return cluster_info

    def mysql_node_detail(self, process_instance, instance):
        if not self.mysql_node_state(process_instance):
            node_info = {
                "mysql_node_state" : 0.0,
                "mysql_uptime" : 0.0,
                "mysql_cpu_usage" : 0.0,
                "mysql_mem_usage" : 0.0,
                "mysql_url" : None
            }
        else:
            node_info = {
                "mysql_node_state" : self.mysql_node_state(process_instance),
                "mysql_uptime" : time() - self.mysql_uptime(process_instance),
                "mysql_cpu_usage" : self.mysql_cpu_usage(process_instance),
                "mysql_mem_usage" : self.mysql_mem_usage(process_instance),
                "mysql_url" : 'http://{0}/dashboard/db/mysql-dashboard-for-prometheus?orgId=1&var-instance={1}'.format(utils.grafana_url(), instance)
            }
        return node_info


def main():
    mysql = MysqlMetrics()
    mysql.mysql_cluster_list()

if __name__ == '__main__':
    main()


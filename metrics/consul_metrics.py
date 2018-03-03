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
# import father directory, append father directory to the sys.path
sys.path.append("..")
from myapp.parse import ParseUtil
from time import time

'''
Scrape consul metrics from Consul Cluster or consul_exporter.
'''

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s',
                    datefmt='%a, %d %b %Y %H:%M:%S')
import sys
logger = logging.getLogger(sys.path[0] + 'consul_metrics')


class ConsulMetrics(object):

    def __init__(self):
        pass

    def ip_list(self):
        '''
        return consul_ip list
        '''
        ip_list = []
        try:
            list = re.split(r'[,\s]\s*', monitor_params.consul_ip.strip())
        except:
            logging.error("Can't split consul_ip. Check the consul_ip in monitor_params.py.")
            sys.exit(1)
        else:
            ip_list = list
        
        print ip_list
        return ip_list


    def raft_peers(self):
        '''
        count how many peers in the cluster via HTTP API.
        '''
        ip_list = self.ip_list()
        consul_port = monitor_params.consul_port
        list_length = len(ip_list)
        result = []

        for i in range(list_length):
            url = 'http://{0}:{1}/v1/status/peers'.format(ip_list[i], consul_port)
            logging.info("start GET %s", url)
            try:
                response = requests.get(url, timeout=5)
                response.raise_for_status()
            except requests.RequestException as e:
                logging.error("Connection Error happends, please check url. Error message: %s" % (e))
                continue
            else:
                res = response.json()
                break
        for i in range(len(res)):
            result.append(res[i].split(":")[0])
        logging.info("raft peers are: %s, and numbers of peers are: %s" % (result, len(result)))
        return [result, float(len(result))]

    def catalog_nodes(self):
        '''
        count how many nodes in the cluster via HTTP API.
        '''
        ip_list = self.ip_list()
        consul_port = monitor_params.consul_port
        list_length = len(ip_list)
        node_list = []

        for i in range(list_length):
            url = 'http://{0}:{1}/v1/catalog/nodes'.format(ip_list[i], consul_port)
            logging.info("start GET %s", url)
            try:
                response = requests.get(url, timeout=5)
                response.raise_for_status()
            except requests.RequestException as e:
                logging.error("Connection Error happends, please check url. Error message: %s" % (e))
                continue
            else:
                result = response.json()
                break
        if result:
            for i in range(len(result)):
                node_list.append(result[i]['Node'])
        else:
            logging.error('No node in the catalog, please Check.')

        return node_list
    
    def catalog_services(self):
        '''
        count how many services in the cluster via HTTP API.
        '''
        node_list = self.catalog_nodes()
        ip_list = self.ip_list()
        consul_port = monitor_params.consul_port
        list_length = len(ip_list)
        service_list = {}
        service_count = 0

        for node_name in range(len(node_list)):
            for ip in range(list_length):
                url = 'http://{0}:{1}/v1/catalog/node/{2}'.format(ip_list[ip], consul_port, node_list[node_name])
                logging.info("start GET %s", url)
                try:
                    response = requests.get(url, timeout=5)
                    response.raise_for_status()
                except requests.RequestException as e:
                    logging.error("Connection Error happends, please check url. Error message: %s" % (e))
                    continue
                else:
                    result = response.json()
                    break
            if result:
                logging.info("{0} services in node {1}.".format(len(result['Services']), node_list[node_name]))
                service_list.setdefault(node_list[node_name], len(result['Services']))
                service_count += len(result['Services'])
            else:
                service_list.setdefault(node_list[node_name], 0)
        logging.info("There are/is {0} service(s) in cluster nodes. ".format(service_count))
        return service_count

    def consul_process_instance(self):
        '''
        @return list of consul instances.
        '''
        instances = utils.get_instances(monitor_params.consul_ip, monitor_params.process_exporter_port)
        return instances

    def instance_info(self):
        instance_list = utils.get_instances(monitor_params.consul_ip, monitor_params.consul_exporter_port)
        return instance_list


    def consul_cluster_state(self):
        '''
        Once 1 leader down, more than half peers left in the cluster, the cluster can elected a new leader.
        So the cluster can work well.
        '''
        success_count = 0.0
        members_count = len(self.ip_list())
        process_instances = self.consul_process_instance()

        for i in range(len(process_instances)):
            consul_up = self.consul_node_state(process_instances[i])
            if consul_up:
                success_count += 1
            else:
                continue
        if (success_count >= (int(members_count/2) + 1)):
            state = 1.0
        else:
            state = 0.0
        logging.info("success count is: %s, and state is %s" % (success_count, state))
        return [state,success_count]

    
    def consul_node_state(self, process_instance):
        '''
        @return a float value 1 or 0, indicating the node state up or down.
        '''
        state = {}
        url = utils.prometheus_url()
        param = {
            "query": 'consul_process_up{{instance="{0}"}}'.format(process_instance)
        }
        response = ParseUtil.request_metrics(url, param)
        for i in range(len(response)):
            state.setdefault(response[i]['metric']['instance'], response[i]['value'][1])
        if state.has_key(process_instance):
            print float(state[process_instance])
            return float(state[process_instance])
        else:
            logging.error("No instance in the consul cluster, consul node {0} down.".format(process_instance))
            return 0.0


    def consul_cpu_usage(self, process_instance):
        '''
        @return a float value 1 or 0, indicating the node state up or down.
        '''
        cpu_usage = {}
        url = utils.prometheus_url()
        param = {
            "query": 'consul_cpu_percentage{{instance="{0}"}}'.format(process_instance)
        }
        response = ParseUtil.request_metrics(url, param)
        for i in range(len(response)):
            cpu_usage.setdefault(response[i]['metric']['instance'], response[i]['value'][1])
        if cpu_usage.has_key(process_instance):
            print float(cpu_usage[process_instance])
            return float(cpu_usage[process_instance])
        else:
            logging.error("Error happends. No instance in the consul cluster, please check.")
            return None

    def consul_uptime(self, process_instance):
        '''
        @return a float value 1 or 0, indicating the node state up or down.
        '''
        uptime = {}
        url = utils.prometheus_url()
        param = {
            "query": 'consul_running_time_seconds_total{{instance="{0}"}}'.format(process_instance)
        }
        response = ParseUtil.request_metrics(url, param)
        for i in range(len(response)):
            uptime.setdefault(response[i]['metric']['instance'], response[i]['value'][1])
        if uptime.has_key(process_instance):
            print float(uptime[process_instance])
            return float(uptime[process_instance])
        else:
            logging.error("Error happends. No instance in the consul cluster, please check.")
            return None

    def consul_mem_usage(self, process_instance):
        '''
        @return a float value 1 or 0, indicating the node state up or down.
        '''
        mem_usage = {}
        url = utils.prometheus_url()
        param = {
            "query": 'sum by (instance)(consul_memory_usage_bytes_total{{instance="{0}", mode=~"rss|vms|shared"}})'.format(process_instance)
        }
        response = ParseUtil.request_metrics(url, param)
        for i in range(len(response)):
            mem_usage.setdefault(response[i]['metric']['instance'], response[i]['value'][1])
        if mem_usage.has_key(process_instance):
            print float(mem_usage[process_instance])
            return float(mem_usage[process_instance])
        else:
            logging.error("Error happends. No instance in the consul cluster, please check.")
            return None           


    def consul_cluster_list(self):
        process_instances = self.consul_process_instance()
        instances = self.instance_info()
        uptime = time()
        for i in range(len(process_instances)):
            state = self.consul_node_state(process_instances[i])
            if state:
                uptime = self.consul_uptime(process_instances[i])
                break
            else:
                continue

        node_info = []
        for i in range(len(process_instances)):
            print "consul process_instance=".format(process_instances[i])
            node_info.append(self.consul_node_detail(process_instances[i], process_instances[i]))
            print "consul node_info=".format(node_info)

        cluster_info = {
            "consul_cluster_state" : self.consul_cluster_state()[0],
            "consul_total_nodes" : float(len(self.ip_list())),
            "consul_healthy_nodes" : self.consul_cluster_state()[1],
            "consul_uptime" : time() - uptime,
            "consul_nodes_info": node_info
        }
        return cluster_info

    def consul_node_detail(self, process_instance, instance):
        if not self.consul_node_state(process_instance):
            node_info = {
                "consul_node_state" : 0.0,
                "consul_uptime" : 0.0,
                "consul_cpu_usage" : 0.0,
                "consul_mem_usage" : 0.0,
                "consul_url" : None
            }
        else:
            node_info = {
                "consul_node_state" : self.consul_node_state(process_instance),
                "consul_uptime" : time() - self.consul_uptime(process_instance),
                "consul_cpu_usage" : self.consul_cpu_usage(process_instance),
                "consul_mem_usage" : self.consul_mem_usage(process_instance),
                "consul_url" : 'http://{0}/dashboard/db/consul-dashboard-for-prometheus?orgId=1&var-instance={1}'.format(utils.grafana_url(), instance)
            }
        return node_info


def main():
    consul = ConsulMetrics()
    consul.consul_cluster_list()

if __name__ == '__main__':
    main()
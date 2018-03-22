#!/usr/bin/python
#-*- coding:utf-8 -*-
import sys
import re
import logging

import utils
from utils import ServiceInfo
sys.path.append("..")
import myapp.params as params
from myapp.parse import ParseUtil
from time import time

'''
    Scrape common metrics from Prometheus.
'''

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s',
                    datefmt='%a, %d %b %Y %H:%M:%S')

logger = logging.getLogger(sys.path[0] + 'common_metrics')

class CommonMetrics(ServiceInfo):

    def __init__(self, process_exporter_name, service_name):
        ServiceInfo.__init__(self, process_exporter_name)
        self._service_name = service_name
        if "mysqld" in service_name:
            self._instances = self.instance_info("mysqld_exporter")
        else:
            self._instances = self.instance_info(service_name)
        self._service_instance = self._instances['service_instance']
        self._process_instance = self._instances['process_instance']
        self._prom_url = self.prometheus_url()
        self._grafana_url = self.grafana_floating_url()
        self._grafana_instances = self.grafana_floating_instance()
        self._index = self.normal_index()
    
    def cluster_state(self):
        '''
        @return cluster state and the numbers of healthy nodes.
        '''
        state = 0.0
        success_count = 0.0

        for i in range(len(self._process_instance)):
            common_up = self.node_state(self._process_instance[i])
            if common_up:
                success_count +=1
            else:
                continue
        if success_count >= 1:
            state = 1.0
        logging.debug("cluster state is %s" % (state))
        return [state, success_count]

    def node_state(self, process_instance):
        '''
        @return a float value 1 or 0, indicating the node state up or down.
        '''
        state = {}
        param = {
            "query": '{0}_process_up{{instance="{1}"}}'.format(self._service_name, process_instance)
        }
        response = ParseUtil.request_metrics(self._prom_url, param)
        for i in range(len(response)):
            state.setdefault(response[i]['metric']['instance'], response[i]['value'][1])
        if state.has_key(process_instance):
            return float(state[process_instance])
        else:
            logging.error("No instance in the {0} cluster, node {1} down.".format(self._service_name, process_instance))
            return 0.0


    def cpu_usage(self, process_instance):
        '''
        @return components cpu usage.
        '''
        cpu_usage = {}
        param = {
            "query": '{0}_cpu_percentage{{instance="{1}"}}'.format(self._service_name, process_instance)
        }
        response = ParseUtil.request_metrics(self._prom_url, param)
        for i in range(len(response)):
            cpu_usage.setdefault(response[i]['metric']['instance'], response[i]['value'][1])
        if cpu_usage.has_key(process_instance):
            return float(cpu_usage[process_instance])
        else:
            logging.error("No instance in the {0} cluster, get {1} cpu usage failed.".format(self._service_name, process_instance))
            return None

    def uptime(self, process_instance):
        '''
        @return a float value of create time.
        '''
        uptime = {}
        param = {
            "query": '{0}_running_time_seconds_total{{instance="{1}"}}'.format(self._service_name, process_instance)
        }
        response = ParseUtil.request_metrics(self._prom_url, param)
        for i in range(len(response)):
            uptime.setdefault(response[i]['metric']['instance'], response[i]['value'][1])
        if uptime.has_key(process_instance):
            return float(uptime[process_instance])
        else:
            logging.error("No instance in the {0} cluster, get {1} uptime failed.".format(self._service_name, process_instance))
            return None

    def mem_usage(self, process_instance):
        '''
        @return components memory usage.
        '''
        mem_usage = {}
        param = {
            "query": 'sum by (instance)({0}_memory_usage_bytes_total{{instance="{1}", mode=~"rss|vms|shared"}})'.format(self._service_name, process_instance)
        }
        response = ParseUtil.request_metrics(self._prom_url, param)
        for i in range(len(response)):
            mem_usage.setdefault(response[i]['metric']['instance'], response[i]['value'][1])
        if mem_usage.has_key(process_instance):
            return float(mem_usage[process_instance])
        else:
            logging.error("No instance in the {0} cluster, get {1} memory usage failed.".format(self._service_name, process_instance))
            return None           


    def cluster_list(self):
        cluster_state = self.cluster_state()
        uptime = time()
        for i in range(len(self._process_instance)):
            state = self.node_state(self._process_instance[i])
            if state:
                uptime = self.uptime(self._process_instance[i])
                break
            else:
                continue

        node_info = []
        if "grafana_server" in self._service_name or "prometheus" in self._service_name:
            logging.debug("grafana_instances = {0}".format(self._grafana_instances))
            for i in range(len(self._process_instance)):
                logging.debug("prom_index={0}, grafana_index={1}".format(self._prom_index, self._grafana_index))
                grafana_err_index = self.get_err_instance_index()['grafana_err_index']
                prom_err_index = self.get_err_instance_index()['prom_err_index']
                if self._prom_index != self._grafana_index:
                    '''如果不等说明要么是grafana挂了，要么是prometheus挂了，url需要全部更新为可用url'''
                    node_info.append(self.node_detail(self._process_instance[i], self._service_instance[i], self._grafana_instances[self._index]))
                elif 1 in grafana_err_index or 1 in prom_err_index:
                    '''
                       两个index相等，不能说明prom和grafana均正常，只能说明有可能grafana1和prome1正常，其他是否正常未知。
                       因此，增加判断，获取异常的prometheus和grafana的index,均为数组形式.
                    '''
                    node_info.append(self.node_detail(self._process_instance[i], self._service_instance[i], self._grafana_instances[self._index]))
                else:
                    node_info.append(self.node_detail(self._process_instance[i], self._service_instance[i], self._grafana_instances[i]))
        else:
            for i in range(len(self._process_instance)):
                node_info.append(self.node_detail(self._process_instance[i], self._service_instance[i]))

        cluster_info = {
            "{0}_cluster_state".format(self._service_name) : cluster_state[0],
            "{0}_total_nodes".format(self._service_name) : float(len(self._process_instance)),
            "{0}_healthy_nodes".format(self._service_name) : cluster_state[1],
            "{0}_uptime".format(self._service_name) : time() - uptime,
            "{0}_nodes_info".format(self._service_name) : node_info
        }
        return cluster_info

    def node_detail(self, process_instance, service_instance, *args):
        board_name = re.sub('([a-z0-9])_([a-z0-9])', r'\1-\2', self._service_name).lower()
        node_state = self.node_state(process_instance)
        if "mysqld" in self._service_name:
            instance = service_instance
        else:
            instance = process_instance

        if "prometheus" in self._service_name:
            service_url = 'http://{0}/dashboard/db/{1}-dashboard-for-prometheus?orgId=1&kiosk'.format(args[0], board_name)
        elif "grafana_server" in self._service_name:
            service_url = 'http://{0}/dashboard/db/{1}-dashboard-for-prometheus?orgId=1&var-instance={2}&kiosk'.format(args[0], board_name, service_instance)
        else:
            service_url = 'http://{0}/dashboard/db/{1}-dashboard-for-prometheus?orgId=1&var-instance={2}&kiosk'.format(self._grafana_url, board_name, instance)

        if not node_state:
            node_info = {
                "{0}_node_state".format(self._service_name) : 0.0,
                "{0}_uptime".format(self._service_name) : 0.0,
                "{0}_cpu_usage".format(self._service_name) : 0.0,
                "{0}_mem_usage".format(self._service_name) : 0.0,
                "{0}_url".format(self._service_name) : None
            }
        else:
            node_info = {
                "{0}_node_state".format(self._service_name) : node_state,
                "{0}_uptime".format(self._service_name) : time() - self.uptime(process_instance),
                "{0}_cpu_usage".format(self._service_name) : self.cpu_usage(process_instance),
                "{0}_mem_usage".format(self._service_name) : self.mem_usage(process_instance),
                "{0}_url".format(self._service_name) : service_url
            }
        return node_info

def main():
    service_name = "prometheus"
    process_name = "process_status_exporter"
    common = CommonMetrics(process_name, service_name)
    from pprint import pprint
    pprint(common.cluster_list())


    service_name = "grafana_server"
    common2 = CommonMetrics(process_name, service_name)
    pprint(common2.cluster_list())

if __name__ == '__main__':
    main()

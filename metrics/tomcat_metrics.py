#!/usr/bin/python
#-*- coding:utf-8 -*-
import sys
import logging

import utils
sys.path.append("..")
import myapp.params as params
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

    def __init__(self, process_exporter_name):
        CommonMetrics.__init__(self, process_exporter_name, "tomcat")
        self.master_name = "tomcat_master"
        self.tenant_name = "tomcat_tenant"
        self.master_instance_infos = self.instance_info(self.master_name)
        self.tenant_instance_infos = self.instance_info(self.tenant_name)
        self._master_instance = self.master_instance_infos['service_instance']
        self._tenant_instance = self.tenant_instance_infos['service_instance']
        self._process_instance = self.master_instance_infos['process_instance']

    def tomcat_node_state(self, role, process_instance):
        '''
        @return a float value 1 or 0, indicating the node state up or down.
        '''
        state = {}
        param = {
            "query": '{0}_process_up{{instance="{1}"}}'.format(role, process_instance)
        }
        response = ParseUtil.request_metrics(self._prom_url, param)
        for i in range(len(response)):
            state.setdefault(response[i]['metric']['instance'], response[i]['value'][1])
        if state.has_key(process_instance):
            return float(state[process_instance])
        else:
            logging.error("No instance in the tomcat cluster, tomcat {0} node {1} down.".format(role, process_instance))
            return 0.0

    def cluster_state(self):
        '''
        @return tomcat cluster state, and the numbers of healthy nodes.
        '''
        state = 0.0
        success_count = 0.0
        master_count = 0.0
        tenant_count = 0.0

        for i in range(len(self._process_instance)):
            master_up = self.tomcat_node_state(self.master_name, self._process_instance[i])
            tenant_up = self.tomcat_node_state(self.tenant_name, self._process_instance[i])
            if master_up:
                master_count += 1
            if tenant_up:
                tenant_count += 1
        success_count = master_count + tenant_count
        if master_count >= 1 and tenant_count >=1:
            state = 1.0
        logging.debug("tomcat state is %s" % (state))
        return [state, success_count]

    def tomcat_cpu_usage(self, role, process_instance):
        '''
        @return a float value 1 or 0, indicating the node state up or down.
        '''
        cpu_usage = {}
        param = {
            "query": '{0}_cpu_percentage{{instance="{1}"}}'.format(role, process_instance)
        }
        response = ParseUtil.request_metrics(self._prom_url, param)
        for i in range(len(response)):
            cpu_usage.setdefault(response[i]['metric']['instance'], response[i]['value'][1])
        if cpu_usage.has_key(process_instance):
            return float(cpu_usage[process_instance])
        else:
            logging.error("No instance in the tomcat cluster, get tomcat {0} node {1} cpu usage failed.".format(role, process_instance))
            return None

    def tomcat_uptime(self, role, process_instance):
        '''
        @return a float value 1 or 0, indicating the node state up or down.
        '''
        uptime = {}
        param = {
            "query": '{0}_running_time_seconds_total{{instance="{1}"}}'.format(role, process_instance)
        }
        response = ParseUtil.request_metrics(self._prom_url, param)
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
        param = {
            "query": 'sum by (instance)({0}_memory_usage_bytes_total{{instance="{1}", mode=~"rss|vms|shared"}})'.format(role, process_instance)
        }
        response = ParseUtil.request_metrics(self._prom_url, param)
        for i in range(len(response)):
            mem_usage.setdefault(response[i]['metric']['instance'], response[i]['value'][1])
        if mem_usage.has_key(process_instance):
            return float(mem_usage[process_instance])
        else:
            logging.error("No instance in the tomcat cluster, get tomcat {0} node {1} memory usage failed.".format(role, process_instance))
            return None           

    def cluster_list(self):
        uptime = time()
        cluster_state = self.cluster_state()
        for i in range(len(self._process_instance)):
            master_state = self.tomcat_node_state(self.master_name, self._process_instance[i])
            tenant_state = self.tomcat_node_state(self.tenant_name, self._process_instance[i])
            if master_state:
                uptime = self.tomcat_uptime(self.master_name, self._process_instance[i])
                break
            elif tenant_state:
                uptime = self.tomcat_uptime(self.tenant_name, self._process_instance[i])
                break
            else:
                continue

        master_info = []
        tenant_info = []
        for i in range(len(self._master_instance)):
            master_info.append(self.tomcat_node_detail(self.master_name, self._process_instance[i], self._master_instance[i]))
            tenant_info.append(self.tomcat_node_detail(self.tenant_name, self._process_instance[i], self._tenant_instance[i]))

        cluster_info = {
            "tomcat_cluster_state" : cluster_state[0],
            "tomcat_total_nodes" : float(sum([len(self._master_instance), len(self._tenant_instance)])),
            "tomcat_healthy_nodes" : cluster_state[1],
            "tomcat_uptime" : time() - uptime,
            "tomcat_master_info": master_info,
            "tomcat_tenant_info": tenant_info
        }
        return cluster_info

    def tomcat_node_detail(self, role, process_instance, role_instance):

        tomcat_node_state = self.tomcat_node_state(role, process_instance)
        if not tomcat_node_state:
            node_info = {
                "{0}_state".format(role) : 0.0,
                "{0}_uptime".format(role) : 0.0,
                "{0}_cpu_usage".format(role) : 0.0,
                "{0}_mem_usage".format(role) : 0.0,
                "{0}_self._prom_url".format(role) : None
            }
        else:
            node_info = {
                "{0}_node_state".format(role) : tomcat_node_state,
                "{0}_uptime".format(role) : time() - self.tomcat_uptime(role, process_instance),
                "{0}_cpu_usage".format(role) : self.tomcat_cpu_usage(role, process_instance),
                "{0}_mem_usage".format(role) : self.tomcat_mem_usage(role, process_instance),
                "{0}_url".format(role) : 'http://{0}/dashboard/db/tomcat-dashboard-for-prometheus?orgId=1&var-instance={1}&kiosk'.format(self._grafana_url, role_instance)
            }
        return node_info

def main():
    process_name = "process_status_exporter"
    tomcat = TomcatMetrics(process_name)

if __name__ == '__main__':
    main()


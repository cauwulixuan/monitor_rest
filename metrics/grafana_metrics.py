#!/usr/bin/python
#-*- coding:utf-8 -*-
import sys
import logging

import utils
sys.path.append("..")
import myapp.params as params
from common_metrics import CommonMetrics
from time import time

'''
    Scrape consul metrics from Consul Cluster or consul_exporter.
'''

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s',
                    datefmt='%a, %d %b %Y %H:%M:%S')

logger = logging.getLogger(sys.path[0] + 'grafana_metrics')

class GrafanaMetrics(CommonMetrics):

    def __init__(self, process_exporter_name):
        CommonMetrics.__init__(self, process_exporter_name, "grafana_server")

    def cluster_list(self):
        uptime = time()
        for i in range(len(self._process_instance)):
            state = self.node_state(self._process_instance[i])
            if state:
                uptime = self.uptime(self._process_instance[i])
                break
            else:
                continue

        node_info = []
        for i in range(len(self._service_instance)):
            node_info.append(self.grafana_node_detail(self._process_instance[i], self._service_instance[i]))

        cluster_info = {
            "grafana_cluster_state" : self.cluster_state()[0],
            "grafana_total_nodes" : float(len(self._service_instance)),
            "grafana_healthy_nodes" : self.cluster_state()[1],
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
                "grafana_url" : 'http://{0}/dashboard/db/grafana-dashboard-for-prometheus?orgId=1&var-instance={1}&kiosk'.format(self._grafana_url, instance)
            }
        return node_info

def main():
    process_name = "process_status_exporter"
    grafana = GrafanaMetrics(process_name)

if __name__ == '__main__':
    main()


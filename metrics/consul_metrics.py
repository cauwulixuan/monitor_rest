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

logger = logging.getLogger(sys.path[0] + 'consul_metrics')


class ConsulMetrics(CommonMetrics):

    def __init__(self, process_exporter_name):
        CommonMetrics.__init__(self, process_exporter_name, "consul")

    def consul_process_instance(self):
        '''
        @return a list of service process instance according the service_name given in the param.
        '''
        process_instances = []
        ip_list = utils.consul_ip_list()
        for i in range(len(ip_list)):
            process_instances.append("{0}:{1}".format(ip_list[i], self._process_port))
        return process_instances

    def consul_service_instance(self):
        '''
        @return a list of service ip according the service_name given in the param.
        '''
        serivce_instances = []
        ip_list = utils.consul_ip_list()
        for i in range(len(ip_list)):
            serivce_instances.append("{0}:{1}".format(ip_list[i], params.consul_port))
        return serivce_instances


    def cluster_state(self):
        '''
        Once 1 leader down, more than half peers left in the cluster, the cluster can elected a new leader.
        So the cluster can work well.
        '''
        process_instances = self.consul_process_instance()
        state = 0.0
        members_count = float(len(process_instances))
        success_count = 0.0

        for i in range(len(process_instances)):
            consul_up = self.node_state(process_instances[i])
            logging.debug("The state of {0} is {1}".format(process_instances[i], consul_up))
            if consul_up:
                success_count += 1
            else:
                continue
        if (success_count >= (int(members_count/2) + 1)):
            state = 1.0
        else:
            state = 0.0
        logging.debug("success count is: {0}, and state is: {1}".format(success_count, state))
        return [state,success_count]

    def cluster_list(self):
        process_instances = self.consul_process_instance()
        serivce_instances = self.consul_service_instance()
        uptime = time()
        cluster_state = self.cluster_state()
        logging.debug("cluster state is: {0}.".format(cluster_state))
        for i in range(len(process_instances)):
            state = self.node_state(process_instances[i])
            logging.debug("The state of {0} is {1}".format(process_instances[i], state))
            if state:
                uptime = self.uptime(process_instances[i])
                break
            else:
                continue

        node_info = []
        for i in range(len(process_instances)):
            node_info.append(self.node_detail(process_instances[i], serivce_instances[i]))

        cluster_info = {
            "{0}_cluster_state".format(self._service_name) : cluster_state[0],
            "{0}_total_nodes".format(self._service_name) : float(len(process_instances)),
            "{0}_healthy_nodes".format(self._service_name) : cluster_state[1],
            "{0}_uptime".format(self._service_name) : time() - uptime,
            "{0}_nodes_info".format(self._service_name) : node_info
        }
        return cluster_info

def main():
    process_name = "process_status_exporter"
    consul = ConsulMetrics(process_name)

if __name__ == '__main__':
    main()
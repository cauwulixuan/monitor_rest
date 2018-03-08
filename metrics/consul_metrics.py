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
from common_metrics import CommonMetrics
from time import time

'''
Scrape consul metrics from Consul Cluster or consul_exporter.
'''

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s',
                    datefmt='%a, %d %b %Y %H:%M:%S')
import sys
logger = logging.getLogger(sys.path[0] + 'consul_metrics')


class ConsulMetrics(CommonMetrics):
    def __init__(self, name = "consul"):
        self._name = name    
    
    def cluster_state(self, ip):
        '''
        Once 1 leader down, more than half peers left in the cluster, the cluster can elected a new leader.
        So the cluster can work well.
        '''
        success_count = 0.0
        members_count = len(self.ip_list(ip))
        process_instances = self.process_instance(ip)

        for i in range(len(process_instances)):
            consul_up = self.node_state(process_instances[i])
            if consul_up:
                success_count += 1
            else:
                continue
        if (success_count >= (int(members_count/2) + 1)):
            state = 1.0
        else:
            state = 0.0
        logging.info("success count is: {0}, and state is: {1}".format(success_count, state))
        return [state,success_count]

def main():
    consul = ConsulMetrics()
    from pprint import pprint
    pprint(consul.cluster_list(monitor_params.consul_ip))

if __name__ == '__main__':
    main()
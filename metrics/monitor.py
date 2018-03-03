# monitor.py
#!/usr/bin/python
#-*- coding:utf-8 -*-

import os
import sys
import re
import time
import requests
sys.path.append('..')
from myapp.parse import ParseUtil
# from . import monitor_params

import utils
from consul_metrics import ConsulMetrics
from nginx_metrics import NginxMetrics
from tomcat_metrics import TomcatMetrics
from prometheus_metrics import PrometheusMetrics
from grafana_metrics import GrafanaMetrics
from mysql_metrics import MysqlMetrics
from keycloak_metrics import KeycloakMetrics
from knox_metrics import KnoxMetrics
from ambari_server_metrics import AmbariServerMetrics
from ambari_agent_metrics import AmbariAgentMetrics
from ldap_metrics import LdapMetrics


def monitor_metrics():

    consul = ConsulMetrics()
    nginx = NginxMetrics()
    tomcat = TomcatMetrics()
    prometheus = PrometheusMetrics()
    grafana = GrafanaMetrics()
    mysql = MysqlMetrics()
    keycloak = KeycloakMetrics()
    knox = KnoxMetrics()
    ambari_server = AmbariServerMetrics()
    ambari_agent = AmbariAgentMetrics()
    ldap = LdapMetrics()
    
    result = []
    metric_info = {
        "consul_info": consul.consul_cluster_list(),
        "nginx_info" : nginx.nginx_cluster_list(),
        "tomcat_info" : tomcat.tomcat_cluster_list(),
        "prometheus_info" : prometheus.prometheus_cluster_list(),
        "grafana_info" : grafana.grafana_cluster_list(),
        "mysql_info" : mysql.mysql_cluster_list(),
        "keycloak_info" : keycloak.keycloak_cluster_list(),
        "knox_info" : knox.knox_cluster_list(),
        "ambari_server_info" : ambari_server.ambari_server_cluster_list(),
        "ambari_agent_info" : ambari_agent.ambari_agent_cluster_list(),
        "ldap_info" : ldap.ldap_cluster_list()
    }
    result.append(metric_info)

    return result


def main():
    result = monitor_metrics()

if __name__ == '__main__':
    main()
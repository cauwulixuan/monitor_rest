# monitor.py
#!/usr/bin/python
#-*- coding:utf-8 -*-

import sys
import utils
sys.path.append("..")
import myapp.params as params

from common_metrics import CommonMetrics
from consul_metrics import ConsulMetrics
from tomcat_metrics import TomcatMetrics

def monitor_metrics():

    result = []
    metric_info = {}
    name_list = [
        "ambari_agent",
        "ambari_server",
        "nginx",
        "keycloak",
        "knox",
        "slapd",
        "mysqld",
        "prometheus",
        "grafana_server"
    ]
    process_name = "process_status_exporter"
    
    consul = ConsulMetrics(process_name)
    consul_info = consul.cluster_list()
    tomcat = TomcatMetrics(process_name)
    tomcat_info = tomcat.cluster_list()

    for i in range(len(name_list)):
        common = CommonMetrics(process_name, name_list[i])
        metrics = common.cluster_list()
        metric_info.setdefault("{0}_info".format(name_list[i]), metrics)
    metric_info.setdefault("consul_info", consul_info)
    metric_info.setdefault("tomcat_info", tomcat_info)
    result.append(metric_info)
    return result

def main():
    result = monitor_metrics()

if __name__ == '__main__':
    main()
    
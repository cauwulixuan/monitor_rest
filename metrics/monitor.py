# monitor.py
#!/usr/bin/python
#-*- coding:utf-8 -*-

import monitor_params
import utils
from common_metrics import CommonMetrics
from consul_metrics import ConsulMetrics
from tomcat_metrics import TomcatMetrics
from grafana_metrics import GrafanaMetrics


def monitor_metrics():

    name_list = {
        "ambari_agent" : monitor_params.ambari_agent_ip,
        "ambari_server" : monitor_params.ambari_server_ip,
        "keycloak" : monitor_params.keycloak_ip,
        "knox" : monitor_params.knox_ip,
        "slapd" : monitor_params.ldap_ip,
        "mysqld" : monitor_params.mysql_ip,
        "prometheus" : monitor_params.prometheus_ip,
    }

    result = []
    metric_info = {}

    consul = ConsulMetrics()
    consul_info = consul.cluster_list(monitor_params.consul_ip)
    tomcat = TomcatMetrics()
    tomcat_info = tomcat.cluster_list(monitor_params.tomcat_ip)
    grafana = GrafanaMetrics()
    grafana_info = grafana.cluster_list(monitor_params.grafana_ip)

    for name in name_list:
        common = CommonMetrics(name)
        metrics = common.cluster_list(name_list[name])
        metric_info.setdefault("{0}_info".format(name), metrics)
    metric_info.setdefault("consul_info", consul_info)
    metric_info.setdefault("tomcat_info", tomcat_info)
    metric_info.setdefault("grafana_info", grafana_info)

    result.append(metric_info)

    return result


def main():
    result = monitor_metrics()

if __name__ == '__main__':
    main()
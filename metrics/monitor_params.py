#!/usr/bin/env python2
#-*- coding: utf-8 -*-

# consul_ip can be set to several values, seperated by ",".
# consul
consul_ip = "172.16.1.47, 172.16.1.33, 172.16.1.19"
consul_port = "8500"
consul_exporter_port = "9107"

# nginx
# nginx_ip:nginx_stab_port running nginx stab
# nginx_ip:nginx_exporter_port running nginx_exporter
# nginx_ip:nginxlog_exporter_port running nginxlog_exporter
nginx_ip = "172.16.1.47"
nginx_stab_port = "7654"
nginx_exporter_port = "9113"
nginxlog_exporter_port = "4040"
# nginx_instance = "10.110.13.67:9113, 10.110.13.67:9113"

# tomcat
tomcat_ip = "172.16.1.47, 172.16.1.33"
tomcat_master_port = "9011"
tomcat_tenant_port = "9021"

# prometheus
prometheus_virtual_ip = "172.16.1.43"
prometheus_ip = "172.16.1.47, 172.16.1.33"
prometheus_outside_ip = "10.10.6.206, 10.10.6.211"
prometheus_port = "9500"

# grafana version should be v4.6.3 or later
grafana_ip = "172.16.1.47, 172.16.1.33"
grafana_outside_ip = "10.10.6.206, 10.10.6.211"
grafana_port = "3000"
# 

# mysql
mysql_ip = "172.16.1.47, 172.16.1.33"
mysql_exporter_port = "9104"

# process_status_exporter
process_exporter_ip = "172.16.1.47, 172.16.1.33, 172.16.1.19"
process_exporter_port = "9108"

# keycloak
keycloak_ip = "172.16.1.47"
keycloak_port = "9110"

# knox
knox_ip = "172.16.1.47"

# ambari-server
ambari_server_ip = "172.16.1.47"

# ambari-agent
ambari_agent_ip = "172.16.1.47, 172.16.1.33, 172.16.1.19"

# ldap
ldap_ip = "172.16.1.47, 172.16.1.33"
#!/usr/bin/python
#-*- coding:utf-8 -*-

import re, sys
sys.path.append("..")
import myapp.params as params
import logging
import requests
import json
import base64

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s',
                    datefmt='%a, %d %b %Y %H:%M:%S')

logger = logging.getLogger(sys.path[0] + 'utils')

def get_ip_list(ip):
    '''
    @param ip: a ip string, seperated by comma.
    @return a list of ip
    '''
    ip_list = []
    if r',' in ip.strip():
        try:
            list = re.split(r'[,\s]\s*', ip.strip())
        except:
            logging.error("Can't split ip: {0}. Check the ip {0} in params.py.".format(ip))
            sys.exit(1)
        else:
            ip_list = list
    else:
        ip_list.append(ip.strip())
    return ip_list

def consul_ip_list():
    '''
    @return a list of consul ip
    '''
    ip_list = get_ip_list(params.consul_ip)
    return ip_list

def get_consul_instance():
    '''
    @return traverse the consul ip list, find available consul, put together with port as an available consul instance.
    '''
    ip_list = consul_ip_list()
    port = params.consul_port
    success = 0

    for i in range(len(ip_list)):
        url = 'http://{0}:{1}/v1/status/leader'.format(ip_list[i], port)
        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()
        except requests.exceptions.ConnectionError:
            logging.warning("GET {0} failed! Connection Error.".format(url))
            continue
        except requests.RequestException as e:
            logging.warning(e)
            continue
        else:
            logging.info("GET {0} ok! Response code is = {1}".format(url, response.status_code))
            result = response.json()
            if len(result) >= 1:
                success += 1
                consul_instance = "{0}:{1}".format(ip_list[i], port)
                logging.debug("Consul instance is : {0}".format(consul_instance))
                return consul_instance
            else:
                continue
    if not success:
        logging.error("No consul agent available, please check it out.")
        sys.exit(1)

Consul_instance = get_consul_instance()


def get_process_port(process_exporter_name):
    '''
    @return a list of service ip according the service_name given in the param.
    '''
    url = 'http://{0}/v1/catalog/service/{1}'.format(Consul_instance, process_exporter_name)
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
    except requests.exceptions.ConnectionError:
        logging.error("GET {0} failed! Connection Error.".format(url))
    except requests.RequestException as e:
        logging.error(e)
    else:
        logging.info("GET {0} ok! Response code is = {1}".format(url, response.status_code))
        result = response.json()
        if len(result):
            process_port = result[0]['ServicePort']
            logging.debug("The port of {0} is : {1}".format(process_exporter_name, process_port))
        else:
            logging.warning("No process_exporter named {0} in consul cluster, no port found.".format(process_exporter_name))
            process_port = None
        return process_port

def floating_ip_map():
    '''
    http://consul_instance/v1/kv/floating_ip_map?recurse
    @return: a list of floating ip.
    '''
    floating_ip_info = {}
    url = 'http://{0}/v1/kv/floating_ip_map?recurse'.format(Consul_instance)
    logging.info("start GET %s", url)
    try:
        response = requests.get(url)
        response.raise_for_status()
    except requests.RequestException as e:
        logging.error(e)
    else:
        result = response.json()
        for i in range(len(result)):
            floating_ip_info.update(json.loads(base64.b64decode(result[i]['Value']).decode()))
    logging.debug("The floating ip map info is : {0}.".format(floating_ip_info))
    return floating_ip_info

class ServiceInfo(object):

    def __init__(self, process_exporter_name):
        self._process_name = process_exporter_name
        self._process_port = get_process_port(process_exporter_name)        
        self._prom_instances = self.instance_info("prometheus")['service_instance']
        self._prom_index = self.get_instance_index("prometheus")
        self._grafana_index = self.get_instance_index("grafana_server")

    def service_info(self, service_name):
        '''
        @return a dict of service info including service_ip and service_port via the service_name given in the param.
        '''
        service_ip = []
        url = 'http://{0}/v1/catalog/service/{1}'.format(Consul_instance, service_name)
        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()
        except requests.exceptions.ConnectionError:
            logging.error("GET {0} failed! Connection Error.".format(url))
        except requests.RequestException as e:
            logging.error(e)
        else:
            logging.info("GET {0} ok! Response code is = {1}".format(url, response.status_code))
            result = response.json()
            if len(result):
                service_port = result[0]['ServicePort']
                for i in range(len(result)):
                    service_ip.append(result[i]['ServiceAddress'])
            else:
                logging.warning("No service named {0} in consul cluster.".format(service_name))
                service_port = None
            service_info = {
                "service_ip": service_ip,
                "service_port": service_port
            }
            return service_info

    def get_instances(self, ip_list, port):
        '''
        @return instance info, formating on ip:port, via the given ip_list and port.
        '''
        instances = []
        for i in range(len(ip_list)):
            url = "{0}:{1}".format(ip_list[i], port)
            instances.append(url)
        return instances
    
    def instance_info(self, service_name):
        services = self.service_info(service_name)
        service_ip = services['service_ip']
        service_port = services['service_port']
        instances = {}
        instances.setdefault("service_instance", self.get_instances(service_ip, service_port))
        instances.setdefault("process_instance", self.get_instances(service_ip, self._process_port))
        return instances

    def get_err_instance_index(self):
        
        prom_index = set()
        grafana_index = set()
        err_info = {}
        prometheus_instances = self._prom_instances
        instance_infos = self.instance_info("grafana_server")
        service_instances = instance_infos['service_instance']
        process_instances = instance_infos['process_instance']
        for index in range(len(service_instances)):
            for i in range(len(prometheus_instances)):
                prom_url = 'http://{0}/api/v1/query'.format(prometheus_instances[i])
                param = {
                    "query": 'grafana_server_process_up{{instance="{0}"}}'.format(process_instances[index])
                }
                logging.info("start GET %s?%s", prom_url, param)
                try:
                    response = requests.get(prom_url, params=param)
                    response.raise_for_status()
                except requests.exceptions.ConnectionError:
                    logging.error("GET %s?%s failed! Connection Error.", prom_url, param)
                    prom_index.add(i)
                    continue
                except requests.RequestException as e:
                    logging.error(e)
                    continue
                else:
                    logging.info("GET /api/v1/query?%s ok! Response code is = %s", param, response.status_code)
                    result = response.json()
                    if int(result['data']['result'][0]['value'][1]) == 0:
                        grafana_index.add(index)
                    else:
                        continue
        err_info.setdefault("prom_err_index", list(prom_index))
        err_info.setdefault("grafana_err_index", list(grafana_index))
        return err_info

    def get_instance_index(self, service_name):
        '''
        According to service_name(prometheus or grafana_server) to get instance index. 
        '''
        success = 0.0
        prometheus_instances = self._prom_instances
        instance_infos = self.instance_info(service_name)
        service_instances = instance_infos['service_instance']
        process_instances = instance_infos['process_instance']
        for index in range(len(service_instances)):
            for i in range(len(prometheus_instances)):
                prom_url = 'http://{0}/api/v1/query'.format(prometheus_instances[i])
                param = {
                    "query": '{0}_process_up{{instance="{1}"}}'.format(service_name, process_instances[index])
                }
                logging.info("start GET %s?%s", prom_url, param)
                try:
                    response = requests.get(prom_url, params=param)
                    response.raise_for_status()
                except requests.exceptions.ConnectionError:
                    logging.error("GET %s?%s failed! Connection Error.", prom_url, param)
                    continue
                except requests.RequestException as e:
                    logging.error(e)
                    continue
                else:
                    logging.info("GET /api/v1/query?%s ok! Response code is = %s", param, response.status_code)
                    result = response.json()
                    if int(result['data']['result'][0]['value'][1]) == 1:
                        success += 1
                        return index
                    else:
                        continue
        if not success:
            logging.error("No prometheus or grafana available, please check it out.")
            sys.exit(1)
    
    def normal_index(self):
        '''
        @return the index of available prometheus and grafana.
        '''
        if self._prom_index == self._grafana_index:
            logging.debug("prometheus and grafana all normal, index is: {0}".format(self._grafana_index))
            return self._grafana_index
        elif self._prom_index < self._grafana_index:
            ''' prometheus1 ok, but grafana1 down, grafana2 ok.'''
            logging.warning("prometheus1 OK, but grafana1 down, using grafana index, the index is: {0}".format(self._grafana_index))
            return self._grafana_index
        else:
            ''' prometheus1 down, prometheus2 ok, grafana ok.'''
            logging.warning("prometheus1 down, prometheus2 OK. grafana OK, using prometheus index, the index is: {0}".format(self._prom_index))
            return self._prom_index
    
    def prometheus_url(self):
        prometheus_instances = self.instance_info("prometheus")['service_instance']
        index = self.normal_index()
        url = 'http://{0}/api/v1/query'.format(prometheus_instances[index])
        return url
    
    def grafana_floating_url(self):
        floating_instances = self.grafana_floating_instance()
        index = self.normal_index()
        return floating_instances[index]
    
    def grafana_floating_instance(self):
        instances = self.instance_info("grafana_server")['service_instance']
        floating_instances = []
        for i in range(len(instances)):
            instance = instances[i].split(":")
            ip = instance[0]
            port = instance[1]
            map = floating_ip_map()
            if ip in map.keys():
                floating_ip = map[ip]
                floating_instances.append("{0}:{1}".format(floating_ip, port))
                logging.debug("Get grafana ip {0} in floating ip map, grafana floating instance is : {1}.".format(ip, floating_instances[i]))        
            else:
                floating_instances.append(instances[i])
                logging.warning("grafana ip {0} not found in floating ip map, using {0}.".format(ip))
        return floating_instances
        
def main():
    process_exporter_name = "process_status_exporter"
    service = ServiceInfo(process_exporter_name)
    print service.get_instance_index("grafana_server")
    from pprint import pprint
    a = service.get_err_instance_index()
    pprint(a)

if __name__ == '__main__':
    main()
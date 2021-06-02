"""
Pulls data from specified iLO and presents as Prometheus metrics
"""
from __future__ import print_function
from _socket import gaierror
import sys
import hpilo

import time
import prometheus_metrics
from BaseHTTPServer import BaseHTTPRequestHandler
from BaseHTTPServer import HTTPServer
from SocketServer import ForkingMixIn
from prometheus_client import generate_latest, Summary
from urlparse import parse_qs
from urlparse import urlparse

def print_err(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


# Create a metric to track time spent and requests made.
REQUEST_TIME = Summary(
    'request_processing_seconds', 'Time spent processing request')


class ForkingHTTPServer(ForkingMixIn, HTTPServer):
    max_children = 30
    timeout = 30


class RequestHandler(BaseHTTPRequestHandler):
    """
    Endpoint handler
    """
    def return_error(self):
        self.send_response(500)
        self.end_headers()

    def get_health_at_glance(self, common_labels, health_at_glance):            
        if health_at_glance is not None:
            for key, value in health_at_glance.items():
                for status in value.items():
                    if status[0] == 'status':
                        gauge = 'hpilo_{}_gauge'.format(key)
                        if status[1].upper() == 'OK':
                            prometheus_metrics.gauges[gauge].labels(product_name=common_labels['product_name'],
                                                                    server_name=common_labels['server_name']).set(0)
                        elif status[1].upper() == 'DEGRADED':
                            prometheus_metrics.gauges[gauge].labels(product_name=common_labels['product_name'],
                                                                    server_name=common_labels['server_name']).set(1)
                        else:
                            prometheus_metrics.gauges[gauge].labels(product_name=common_labels['product_name'],
                                                                    server_name=common_labels['server_name']).set(2)
    def get_detailed_disk_info(self, common_labels, storage):
        for controller_label, controller_info in storage.items():
            status = storage[controller_label]['status']
            if status.upper() == 'OK':
                prometheus_metrics.gauges['hpilo_hdd_controller_gauge'].labels(product_name=common_labels['product_name'],
                                                        server_name=common_labels['server_name'], controller_label=controller_label).set(0)
            elif status.upper() == 'DEGRADED':
                prometheus_metrics.gauges['hpilo_hdd_controller_gauge'].labels(product_name=common_labels['product_name'],
                                                        server_name=common_labels['server_name'], controller_label=controller_label).set(1)
            else:
                prometheus_metrics.gauges['hpilo_hdd_controller_gauge'].labels(product_name=common_labels['product_name'],
                                                        server_name=common_labels['server_name'], controller_label=controller_label).set(2)            

            for logical_drive in storage[controller_label]['logical_drives']:
                logical_drive_label = logical_drive['label']
                logical_drive_status = logical_drive['status']
                if logical_drive_status.upper() == 'OK':
                    prometheus_metrics.gauges['hpilo_logical_drive_gauge'].labels(product_name=common_labels['product_name'],
                                                            server_name=common_labels['server_name'], controller_label=controller_label, logical_drive_label=logical_drive_label).set(0)
                elif logical_drive_status.upper() == 'DEGRADED':
                    prometheus_metrics.gauges['hpilo_logical_drive_gauge'].labels(product_name=common_labels['product_name'],
                                                            server_name=common_labels['server_name'], controller_label=controller_label, logical_drive_label=logical_drive_label).set(1)
                else:
                    prometheus_metrics.gauges['hpilo_logical_drive_gauge'].labels(product_name=common_labels['product_name'],
                                                            server_name=common_labels['server_name'], controller_label=controller_label, logical_drive_label=logical_drive_label).set(2)

                for physical_drive in logical_drive['physical_drives']:
                    physical_drive_location = physical_drive['location']
                    physical_drive_label = physical_drive['label']
                    physical_drive_status = physical_drive['status']
                    if physical_drive_status.upper() == 'OK':
                        prometheus_metrics.gauges['hpilo_physical_drive_gauge'].labels(product_name=common_labels['product_name'],
                                                                server_name=common_labels['server_name'], controller_label=controller_label, logical_drive_label=logical_drive_label, physical_drive_label=physical_drive_label, location=physical_drive_location).set(0)
                    elif physical_drive_status.upper() == 'DEGRADED':
                        prometheus_metrics.gauges['hpilo_physical_drive_gauge'].labels(product_name=common_labels['product_name'],
                                                                server_name=common_labels['server_name'], controller_label=controller_label, logical_drive_label=logical_drive_label, physical_drive_label=physical_drive_label, location=physical_drive_location).set(0)
                    else:
                        prometheus_metrics.gauges['hpilo_physical_drive_gauge'].labels(product_name=common_labels['product_name'],
                                                                server_name=common_labels['server_name'], controller_label=controller_label, logical_drive_label=logical_drive_label, physical_drive_label=physical_drive_label, location=physical_drive_location).set(0)

    def get_fans_info(self, common_labels, fans):
        for _, fan in fans.items():
            status = fan['status']
            speed_value = fan['speed'][0]
            speed_unit = fan['speed'][1]
            zone = fan['zone']
            label = fan['label']

            prometheus_metrics.gauges['hpilo_fan_speed_gauge'].labels(product_name=common_labels['product_name'], server_name=common_labels['server_name'],
                                                                unit=speed_unit, zone=zone, label=label).set(speed_value)

            if status.upper() == 'OK':
                prometheus_metrics.gauges['hpilo_fan_health_gauge'].labels(product_name=common_labels['product_name'], server_name=common_labels['server_name'],
                                                                            zone=zone, label=label).set(0)
            elif status.upper() == 'DEGRADED':
                prometheus_metrics.gauges['hpilo_fan_health_gauge'].labels(product_name=common_labels['product_name'], server_name=common_labels['server_name'],
                                                                            zone=zone, label=label).set(1)
            else:
                prometheus_metrics.gauges['hpilo_fan_health_gauge'].labels(product_name=common_labels['product_name'], server_name=common_labels['server_name'],
                                                                            zone=zone, label=label).set(2)



    def do_GET(self):
        """
        Process GET request

        :return: Response with Prometheus metrics
        """
        # this will be used to return the total amount of time the request took
        start_time = time.time()
        # get parameters from the URL
        url = urlparse(self.path)
        # following boolean will be passed to True if an error is detected during the argument parsing
        error_detected = False
        query_components = parse_qs(urlparse(self.path).query)

        ilo_host = None
        ilo_port = None
        ilo_user = None
        ilo_password = None
        try:
            ilo_host = query_components['ilo_host'][0]
            ilo_port = int(query_components['ilo_port'][0])
            ilo_user = query_components['ilo_user'][0]
            ilo_password = query_components['ilo_password'][0]
        except KeyError, e:
            print_err("missing parameter %s" % e)
            self.return_error()
            error_detected = True

        return_summary = True
        return_disks = True
        return_fans = True
        if 'config' in query_components:
            if 'no_summary' in query_components['config'][0]:
                return_summary = False
            if 'no_disks' in query_components['config'][0]:
                return_disks = False
            if 'no_fans' in query_components['config'][0]:
                return_fans = False

        if url.path == self.server.endpoint and ilo_host and ilo_user and ilo_password and ilo_port:

            ilo = None
            try:
                ilo = hpilo.Ilo(hostname=ilo_host,
                                login=ilo_user,
                                password=ilo_password,
                                port=ilo_port, timeout=10)
            except hpilo.IloLoginFailed:
                print("ILO login failed")
                self.return_error()
            except gaierror:
                print("ILO invalid address or port")
                self.return_error()
            except hpilo.IloCommunicationError, e:
                print(e)

            # get product and server name
            common_labels = {}
            try:
                common_labels['product_name'] = ilo.get_product_name()
            except:
                common_labels['product_name'] = "Unknown HP Server"

            try:
                common_labels['server_name'] = ilo.get_server_name()
                if common_labels['server_name'] == "":
                    common_labels['server_name'] = ilo_host
            except:
                common_labels['server_name'] = ilo_host

            # get health
            embedded_health = ilo.get_embedded_health()

            if return_summary:
                self.get_health_at_glance(common_labels, embedded_health['health_at_a_glance'])

            if return_disks:
                if embedded_health['storage'] == "null":
                    # 'storage' is null if drives are in back of server rather than in the front plane.
                    # Does not require AMS for disk information but AMS must be installed and running for 
                    # SAS/SATA controller health information.
                    print("Detailed disk information is unavailable.")
                else:
                    self.get_detailed_disk_info(common_labels, embedded_health['storage'])

            if return_fans:
                self.get_fans_info(common_labels, embedded_health['fans'])

            #for iLO3 patch network
            if ilo.get_fw_version()["management_processor"] == 'iLO3':
                print_err('Unknown iLO nic status')
            else:
                # get nic information
                for nic_name,nic in embedded_health['nic_information'].items():
                   try:
                       value = ['OK','Disabled','Unknown','Link Down'].index(nic['status'])
                   except ValueError:
                       value = 4
                       print_err('unrecognised nic status: {}'.format(nic['status']))

                   prometheus_metrics.hpilo_nic_status_gauge.labels(product_name=common_labels['product_name'],
                                                                    server_name=common_labels['server_name'],
                                                                    nic_name=nic_name,
                                                                    ip_address=nic['ip_address']).set(value)

            # get firmware version
            fw_version = ilo.get_fw_version()["firmware_version"]
            # prometheus_metrics.hpilo_firmware_version.set(fw_version)
            prometheus_metrics.hpilo_firmware_version.labels(product_name=common_labels['product_name'],
                                                            server_name=common_labels['server_name']).set(fw_version)

            # get the amount of time the request took
            REQUEST_TIME.observe(time.time() - start_time)

            # generate and publish metrics
            metrics = generate_latest(prometheus_metrics.registry)
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(metrics)

        elif url.path == '/':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            self.wfile.write("""<html>
            <head><title>HP iLO Exporter</title></head>
            <body>
            <h1>HP iLO Exporter</h1>
            <p>Visit <a href="/metrics">Metrics</a> to use.</p>
            </body>
            </html>""")

        else:
            if not error_detected:
                self.send_response(404)
                self.end_headers()


class ILOExporterServer(object):
    """
    Basic server implementation that exposes metrics to Prometheus
    """

    def __init__(self, address='0.0.0.0', port=8080, endpoint="/metrics"):
        self._address = address
        self._port = port
        self.endpoint = endpoint

    def print_info(self):
        print_err("Starting exporter on: http://{}:{}{}".format(self._address, self._port, self.endpoint))
        print_err("Press Ctrl+C to quit")

    def run(self):
        self.print_info()

        server = ForkingHTTPServer((self._address, self._port), RequestHandler)
        server.endpoint = self.endpoint

        try:
            while True:
                server.handle_request()
        except KeyboardInterrupt:
            print_err("Killing exporter")
            server.server_close()

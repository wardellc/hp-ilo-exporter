# HP iLO Metrics Exporter

Blackbox likes exporter used to exports HP Server Integrated Lights Out (iLO) states to Prometheus.

### Gauges

Here are the status code of gauge
```
0 - OK
1 - Degraded
2 - Dead (Other)
```


### Health summary output example

Example of status of your iLO
```
health_at_a_glance:
  battery: {status: OK}
  bios_hardware: {status: OK}
  fans: {redundancy: Redundant, status: OK}
  memory: {status: OK}
  network: {status: Link Down},
  power_supplies: {redundancy: Redundant, status: OK}
  processor: {status: OK}
  storage: {status: Degraded}
  temperature: {status: OK}
  vrm: {status: Ok}
  drive: {status: Ok}
```

The returned output would be:
```
hpilo_battery{product_name="ProLiant DL360 Gen9",server_name="name.fqdn.domain"} 0.0
hpilo_storage{product_name="ProLiant DL360 Gen9",server_name="name.fqdn.domain"} 1.0
hpilo_fans{product_name="ProLiant DL360 Gen9",server_name="name.fqdn.domain"} 0.0
hpilo_bios_hardware{product_name="ProLiant DL360 Gen9",server_name="name.fqdn.domain"} 0.0
hpilo_memory{product_name="ProLiant DL360 Gen9",server_name="name.fqdn.domain"} 0.0
hpilo_power_supplies{product_name="ProLiant DL360 Gen9",server_name="name.fqdn.domain"} 0.0
hpilo_processor{product_name="ProLiant DL360 Gen9",server_name="name.fqdn.domain"} 0.0
hpilo_network{product_name="ProLiant DL360 Gen9",server_name="name.fqdn.domain"} 2.0
hpilo_temperature{product_name="ProLiant DL360 Gen9",server_name="name.fqdn.domain"} 0.0
hpilo_vrm{product_name="ProLiant DL380 Gen6",server_name="name.fqdn.domain"} 0.0
hpilo_drive{product_name="ProLiant DL380 Gen6",server_name="name.fqdn.domain"} 0.0
hpilo_firmware_version{product_name="ProLiant DL360 Gen9",server_name="name.fqdn.domain"} 2.5
```

### Disk drive health output example

Example of status of your iLO (shortened)
```
"storage": {
  "Controller in Slot 2": {
    "status": "OK",
    "logical_drives": [
      {
        "status": "OK",
        "label": "01",
        "physical_drives": [
          {
            "status": "OK",
            "label": "Port 2I Box 1 Bay 1",
            "location": "Port 2I Box 1 Bay 1",
          }
        ]
      }
    ],
    "label": "Controller in Slot 2"
  }
}
```

The returned output would be:
```
hpilo_hdd_controller{controller_label="Controller in Slot 2",product_name="ProLiant DL360 Gen9",server_name="name.fqdn.domain"} 0.0
hpilo_logical_drive{controller_label="Controller in Slot 2",logical_drive_label="01",product_name="ProLiant DL360 Gen9",server_name="name.fqdn.domain"} 0.0
hpilo_physical_drive{controller_label="Controller in Slot 2",location="Port 2I Box 1 Bay 1",logical_drive_label="01",physical_drive_label="Port 2I Box 1 Bay 1",product_name="ProLiant DL360 Gen9",server_name="name.fqdn.domain"} 0.0
```

### Fan speed and health output example

Example of status of your iLO (shortened)
```
"fans": {
  "Fan 2": {
    "status": "OK",
    "speed": [
      35,
      "Percentage"
    ],
    "zone": "System",
    "label": "Fan 2"
}
```

The returned output would be:
```
hpilo_fan_speed{label="Fan 2",product_name="ProLiant DL360 Gen9",server_name="name.fqdn.domain",unit="Percentage",zone="System"} 35.0
hpilo_fan_health{label="Fan 2",product_name="ProLiant DL360 Gen9",server_name="name.fqdn.domain",zone="System"} 0.0
```

### Temperature output example

Note: at present only temperature values are returned where 'status' is 'OK'.

Example of status of your iLO (shortened)
```
"temperature": {
"38-PCI 4 Zone": {
  "status": "OK",
  "currentreading": [
    26,
    "Celsius"
  ],
  "label": "38-PCI 4 Zone",
  "critical": [
    72,
    "Celsius"
  ],
  "caution": [
    67,
    "Celsius"
  ],
  "location": "I/O Board"
}
```

The returned output would be:
```
hpilo_temperature_measurement{caution_value="67",critical_value="72",label="38-PCI 4 Zone",location="I/O Board",product_name="ProLiant DL360 Gen9",server_name="name.fqdn.domain",unit="Celsius"} 26.0
```


### Installing

You can install exporter on the server directly or on separate machine.
To run, you must have `Python` and `pip` installed.

To install with `pip`:
```
pip install -e $HPILO_EXPORTER_DIR
```

Then just:
```
hpilo-exporter [--address=0.0.0.0 --port=9416 --endpoint="/metrics"]
```


HPILO is also available on [Pypi](https://pypi.org/project/hpilo-exporter/) so it can be installed directly:

```
pip install hpilo-exporter
```

### Docker

Prebuild images are available from the docker repository:
```
idnt/hpilo-exporter:latest
```


To build the image yourself
```
docker build --rm -t hpilo-exporter .
```

To run the container
```
docker run -p 9416:9416 hpilo-exporter:latest
```

You can then call the web server on the defined endpoint, `/metrics` by default.
```
curl 'http://127.0.0.1:9416/metrics?ilo_host=127.0.0.1&ilo_port=443&ilo_user=admin&ilo_password=admin'
```

To not return disk drive health, temperatures and fan info.
```
curl 'http://127.0.0.1:9416/metrics?ilo_host=127.0.0.1&ilo_port=443&ilo_user=admin&ilo_password=admin&config=no_disks,no_temperatures,no_fans'
```

Passing argument to the docker run command
```
docker run -p 9416:9416 hpilo-exporter:latest --port 9416 --ilo_user my_user --ilo_password my_secret_password
```

### Docker compose

Here is an example of Docker Compose deployment:

```yml
hpilo:
    image: my.registry/hpilo-exporter
    ports:
      - 9416:9416
    command:
      - '--port=9416'
    deploy:
      placement:
        constraints:
          - node.hostname == my_node.domain
```

### Kubernetes

A helm chart is available at [prometheus-helm-addons](https://github.com/IDNT/prometheus-helm-addons).

### Prometheus config

Assuming:
- the exporter is available on `http://hpilo:9416`
- you use same the port,username and password for all your iLO

```yml
- job_name: 'hpilo'
  scrape_interval: 1m
  scrape_timeout: 30s
  params:
    ilo_port: ['443']
    ilo_user: ['my_ilo_user']
    ilo_password: ['my_ilo_password']
  static_configs:
    - targets:
      - ilo_fqdn.domain

  relabel_configs:
    - source_labels: [__address__]
      target_label: __param_ilo_host
    - source_labels: [__param_ilo_host]
      target_label: ilo_host
    - target_label: __address__
      replacement: hpilo:8082  # hpilo exporter.
```


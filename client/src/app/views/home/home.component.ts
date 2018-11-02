import { Component, OnInit } from '@angular/core';
import { DataService } from '../../services/data.service';
import { detachEmbeddedView } from '@angular/core/src/view';

export class Tile {
  endPoint: string;
  color: string;
  cols: number;
  rows: number;
  text: string;
  type: string;
  prefix: string;
  suffix: string;
  formatter: any;
  request: any;

  constructor() {}
}

@Component({
  selector: 'app-home',
  templateUrl: './home.component.html',
  styleUrls: ['./home.component.scss'],
})
export class HomeComponent implements OnInit {

  private cpusInitialized = false;

  tiles: any[] = [
    {
      text: 'status',
      endPoint: 'metrics',
      cols: 1,
      rows: 1,
      color: 'lightblue',
      type: 'status',
      prefix: undefined,
      suffix: undefined,
      formatter: undefined
    },
    {
      text: 'uptime',
      endPoint: 'uptime',
      cols: 1,
      rows: 1,
      color: 'lightgreen',
      type: 'duration',
      prefix: undefined,
      suffix: undefined,
      formatter: undefined
    },
    {
      text: 'memory',
      endPoint: 'memory',
      cols: 1,
      rows: 1,
      color:
        'lightblue',
      type: 'string',
      prefix: undefined,
      suffix: 'Mo',
      formatter: (data) => {
        let used: number = data['virtual'][3] / 1024 / 1024;
        let total: number = data['virtual'][0] / 1024 / 1024;
        return `${Math.round(used)}Mo / ${Math.round(total)}Mo`; // Math.round(data.virtual[3] / 1024 / 1024);
      }
    },
    {
      text: 'storage',
      endPoint: 'partitions',
      cols: 1,
      rows: 1,
      color: 'lightblue',
      type: 'string',
      prefix: undefined,
      suffix: undefined,
      formatter: (data) => {
        let used: number = data['usage'][1] / 1024 / 1024;
        let total: number = data['usage'][0] / 1024 / 1024;
        return `${Math.round(used)}Mo / ${Math.round(total)}Mo`;
      }
    },
    {
      text: 'cpu',
      endPoint: 'cpu',
      cols: 1,
      rows: 1,
      color: 'lightblue',
      type: 'string',
      prefix: undefined,
      suffix: undefined,
      formatter: (data) => {
        if (!this.cpusInitialized) {
          const cpus = [];
          let cpuNum = 0;
          data.usage.forEach(element => {
            cpus.push({
              name: 'Cpu load ' + cpuNum,
              data: []
            });

            cpuNum += 1;

            this.initCpus(cpus);
          });
        }
        // this.chart = new ChartsOption(cpus, 'CPU load', 'spline');
        // this.chartOptions = this.chart.options;
        return data.info.count + ' cores';
      }
    },
    {
      text: 'system_info',
      endPoint: 'system_info',
      cols: 1,
      rows: 1,
      color: 'lightblue',
      type: 'string',
      prefix: undefined,
      suffix: undefined,
      formatter: (data) => {
        return data['hostname'];
      }
    },
  ];

  cpu: any;
  memory = {
    onPull: (data, chart) => {
      const x = (new Date()).getTime();
      chart.series[0].addPoint([x, data.virtual[3]], true, true);
      chart.series[1].addPoint([x, data.swap[0]], true, true);
    },
    series:
      [{
        name: 'Used',
        data: this.generateEmptyDatas()
      },
      {
        name: 'Swap',
        data: this.generateEmptyDatas()
      }]
  };

  network = {
    onPull: (data, chart) => {
      const x = (new Date()).getTime();
      const keys = Object.keys(data);
      // console.log(data);

      const incomingBytes = data[keys[0]].incoming.bytes;
      const outgoingBytes = data[keys[0]].outgoing.bytes;

      const dataUnits = ['K', 'M', 'G', 'T'];

      let incomming = incomingBytes;
      let outgoing = outgoingBytes;
      dataUnits.forEach(unit => {
        if (incomingBytes.includes(unit)) {
          incomming = parseInt(incomingBytes.substring(0, incomingBytes.length - 2));
          incomming = incomming * Math.pow(1024, dataUnits.indexOf(unit));
        }
        if (outgoingBytes.includes(unit)) {
          outgoing = parseInt(outgoingBytes.substring(0, outgoingBytes.length - 2));
          outgoing = outgoing * Math.pow(1024, 3);
        }
      });

      chart.series[0].addPoint([x, incomming], true, true);
      chart.series[1].addPoint([x, outgoing], true, true);
    },
    series:
      [{
        name: 'Incoming',
        data: this.generateEmptyDatas()
      },
      {
        name: 'Outgoing',
        data: this.generateEmptyDatas()
      }]
  };

  constructor(private service: DataService) {
  }

  ngOnInit() {
    this.tiles.forEach((tile) => {
      tile.request = {
        last: new Date()
      }
      this.getSimpleIndicator(tile);
    });

    setInterval(() => {
      this.tiles.forEach((tile) => {
        tile.request = {
          last: new Date()
        }
        this.getSimpleIndicator(tile);
      });  
    }, 3000);
  }

  getSimpleIndicator(tile) {
    this.service.get(tile.endPoint).subscribe((data) => {
      if (tile.endPoint.type === 'status') {
        tile.value = true;
      } else if (tile.formatter) {
        tile.value = tile.formatter(data);
      } else {
        tile.value = data;
      }

      tile.request.responseAt = new Date();
      tile.request.duration = (tile.request.responseAt.getTime()- tile.request.last.getTime()) / 1000;
    }, () => {
      tile.value = "Contact lost";
      tile.request.responseAt = new Date();
      tile.request.duration = (tile.request.responseAt.getTime()- tile.request.last.getTime()) / 1000;
    });
  }

  generateEmptyDatas() {
    // generate an array of random data
    // TODO get data history from server side
    const data = [],
      time = (new Date()).getTime();
    let i;
    const NB_MINUTES_MONITOR = 10;
    for (i = -NB_MINUTES_MONITOR * 60; i <= 0; i += 1) {
      data.push({
        x: time + ((i + 3) * 1000),
        y: 0
      });
    }
    return data;
  }

  initCpus(cpus: Array<any>) {

    this.service.get('history/cpu/load').subscribe((data) => {
      
      data.forEach(metricHistoryEntry => {
        let i = 0;
        cpus.forEach(cpusEntry => {
          cpus[i].data.push({
            x: new Date(metricHistoryEntry.date),
            y: metricHistoryEntry[`cpu${i}`]
          });
          i +=1;
        });
      });
      console.log(cpus);

      this.cpu = {
        onPull: (data, chart) => {
          const x = (new Date()).getTime();
          let i = 0;
          data.usage.forEach(element => {
            chart.series[i].addPoint([x, data.usage[i]], true, true);
            i += 1;
          });
        },
        series: cpus
      };
    });

    
    this.cpusInitialized = true;
  }
}

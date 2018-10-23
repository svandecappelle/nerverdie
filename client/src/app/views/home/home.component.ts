import { Component, OnInit } from '@angular/core';
import { DataService } from '../../services/data.service';

export interface Tile {
  endPoint: string;
  color: string;
  cols: number;
  rows: number;
  text: string;
  type: string;
  prefix: string;
  suffix: string;
  formatter: any;
}

@Component({
  selector: 'app-home',
  templateUrl: './home.component.html',
  styleUrls: ['./home.component.scss'],
})
export class HomeComponent implements OnInit {

  private data: any = {};

  tiles: Tile[] = [
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
      type: 'number',
      prefix: undefined,
      suffix: 'Mo',
      formatter: (data) => {
        return Math.round(data.virtual[0] / 1024 / 1024);
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
        let used: number = data['usage'][2] / 1024 / 1024;
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
        const cpus = [];
        let cpuNum = 0;
        data.usage.forEach(element => {
          cpus.push({
            name: 'Cpu load ' + cpuNum,
            data: this.generateEmptyDatas()
          });

          cpuNum += 1;

          this.initCpus(cpus);
        });
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

      let incomingBytes = data[keys[0]].incoming.bytes;
      let outgoingBytes = data[keys[0]].outgoing.bytes;

      if (incomingBytes.includes('M')) {
        incomingBytes = parseInt(incomingBytes.substring(0, incomingBytes.length - 2));
        incomingBytes = incomingBytes * 1024;
      } else if (incomingBytes.includes('K')) {
        incomingBytes = parseInt(incomingBytes.substring(0, incomingBytes.length - 2));
      }

      if (outgoingBytes.includes('M')) {
        outgoingBytes = parseInt(outgoingBytes.substring(0, outgoingBytes.length - 2));
        outgoingBytes = outgoingBytes * 1024;
      } else if (outgoingBytes.includes('K')) {
        outgoingBytes = parseInt(outgoingBytes.substring(0, outgoingBytes.length - 2));
      }

      chart.series[0].addPoint([x, incomingBytes], true, true);
      chart.series[1].addPoint([x, outgoingBytes], true, true);
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
      this.getSimpleIndicator(tile);
    });
  }

  getSimpleIndicator(tile) {
    this.service.get(tile.endPoint).subscribe((data) => {
      if (tile.endPoint.type === 'status') {
        tile.value = 0;
      } else if (tile.formatter) {
        tile.value = tile.formatter(data);
      } else {
        tile.value = data;
      }
    }, () => {
      tile.value = 1;
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
  }
}

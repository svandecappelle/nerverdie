import { Component, OnInit } from '@angular/core';
import * as Highcharts from 'highcharts';

import { ChartsOption } from './charts';
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
            data: (function () {
              // generate an array of random data
              // TODO get data history from server side
              const data = [],
                time = (new Date()).getTime();
              let i;
              for (i = -49; i <= 0; i += 1) {
                data.push({
                  x: time + i * 1000,
                  y: 0
                });
              }
              return data;
            }())
          });

          cpuNum += 1;
        });
        this.chart = new ChartsOption(cpus, 'CPU load');
        this.chartOptions = this.chart.options;
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

  // CPU chart:
  HighchartsCPU = Highcharts; // required
  chart;
  chartOptions;
  chartCallback = (chart) => {
    this.chart.pull.subscribe((initialized) => {
      if (initialized && !this.pending['cpu']) {
        const x = (new Date()).getTime();
        this.pending['cpu'] = true;
        this.service.get('cpu').subscribe((data) => {
          let i = 0;
          data.usage.forEach(element => {
            this.chart.series[i].addPoint([x, data.usage[i]], true, true);
            i += 1;
          });
          this.pending['cpu'] = false;
        });
      }
    });
  };

  HighchartsMemory = Highcharts; // required
  // Memory chart:
  chartMemory = new ChartsOption([{
    name: 'Used',
    data: (function () {
      // generate an array of random data
      // TODO get data history from server side
      const data = [],
        time = (new Date()).getTime();
      let i;
      for (i = -49; i <= 0; i += 1) {
        data.push({
          x: time + i * 1000,
          y: 0
        });
      }
      return data;
    }())
  },
  {
    name: 'Swap',
    data: (function () {
      // generate an array of random data
      // TODO get data history from server side
      const data = [],
        time = (new Date()).getTime();
      let i;
      for (i = -49; i <= 0; i += 1) {
        data.push({
          x: time + i * 1000,
          y: 0
        });
      }
      return data;
    }())
  }], 'Memory load');;
  chartMemoryOptions = this.chartMemory.options;
  chartMemoryCallback = (chart) => {
    this.chartMemory.pull.subscribe((initialized) => {
      if (initialized && !this.pending['memory']) {
        const x = (new Date()).getTime();
        this.pending['memory'] = true;
        this.service.get('memory').subscribe((data) => {
          this.chartMemory.series[0].addPoint([x, data.virtual[3]], true, true);
          this.chartMemory.series[1].addPoint([x, data.swap[0]], true, true);
          this.pending['memory'] = false;
        });
      }
    });
  };

  private pending = {
    cpu: false,
    memory: false,
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
}

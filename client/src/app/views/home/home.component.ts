import { Component, OnInit } from '@angular/core';
import * as Highcharts from 'highcharts';

import { DataService } from '../../services/data.service';

export interface Tile {
  color: string;
  cols: number;
  rows: number;
  text: string;
}

@Component({
  selector: 'app-home',
  templateUrl: './home.component.html',
  styleUrls: ['./home.component.scss'],
})
export class HomeComponent implements OnInit {

  private data: any = {};

  tiles: Tile[] = [
    {text: 'status', cols: 1, rows: 1, color: 'lightblue'},
    {text: 'uptime', cols: 1, rows: 1, color: 'lightgreen'},
    {text: 'memory', cols: 1, rows: 1, color: 'lightblue'},
    {text: 'storage', cols: 1, rows: 1, color: 'lightblue'},
    {text: 'cpu', cols: 1, rows: 1, color: 'lightblue'},
    {text: 'other', cols: 1, rows: 1, color: 'lightblue'},
  ];

  Highcharts = Highcharts; // required
  chartConstructor = 'chart'; // optional string, defaults to 'chart'
  chartOptions = { series: [{
    data: [1, 2, 3]
  }] }; // required
  // chartCallback = function (chart) { ... } // optional function, defaults to null
  updateFlag = false; // optional boolean
  oneToOneFlag = true; // optional boolean, defaults to false
  runOutsideAngular = false; // optional boolean, defaults to false

  constructor(private service: DataService) {
  }

  ngOnInit() {
    this.tiles.forEach((tile) => {
      this.getSimpleIndicator(tile.text);
    });
  }

  getSimpleIndicator(name) {
    if (name === "status") {
      this.service.get('metrics').subscribe((data) => {
        this.data[name] = 'Up';
      }, () => {
        this.data[name] = 'Down';
      });
    } else if (name === "uptime") {
      this.service.get(name).subscribe((data) => {
        this.data[name] = new Date(data);
      });
    } else if (name === "memory") {
      this.service.get(name).subscribe((data) => {
        this.data[name] = data.virtual[0] / 1024 / 1024 + 'Mo';
      });
    } else if (name === "Storage") {
      "250Go";
    } else if (name === "cpu") {
      this.service.get(name).subscribe((data) => {
        this.data[name] = data.info.count + ' cores';
      });
    } else {
      this.service.get(name).subscribe((data) => {
        this.data[name] = data;
      });
    }
  }
}

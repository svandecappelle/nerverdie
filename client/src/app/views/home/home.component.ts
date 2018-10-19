import { Component, OnInit } from '@angular/core';
import * as Highcharts from 'highcharts';


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

  tiles: Tile[] = [
    {text: 'Status', cols: 1, rows: 1, color: 'lightblue'},
    {text: 'Uptime', cols: 1, rows: 1, color: 'lightgreen'},
    {text: 'Memory', cols: 1, rows: 1, color: 'lightblue'},
    {text: 'Storage', cols: 1, rows: 1, color: 'lightblue'},
    {text: 'Cpu', cols: 1, rows: 1, color: 'lightblue'},
    {text: 'Other', cols: 1, rows: 1, color: 'lightblue'},
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

  constructor() {
  }

  ngOnInit() {
  }

  getSimpleIndicator(name) {
    if (name === "Status") {
      return "Up";
    } else if (name === "Uptime") {
      return "1d 4h 56min";
    } else if (name === "Memory") {
      return "8Go";
    } else if (name === "Storage") {
      return "250Go";
    } else if (name === "Cpu") {
      return "4Cores";
    } else {
      return "";
    }
  }
}

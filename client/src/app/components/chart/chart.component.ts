import { Component, OnInit, Input } from '@angular/core';
import * as Highcharts from 'highcharts';


import { ChartsOption } from './charts';
import { DataService } from '../../services/data.service';

@Component({
  selector: 'app-chart',
  templateUrl: './chart.component.html',
  styleUrls: ['./chart.component.css']
})
export class ChartComponent implements OnInit {

  private pending = false;

  private Highcharts = Highcharts; // required
  private chart;

  @Input()
  series: Array<any>;

  @Input()
  title: string;

  @Input()
  type = 'area';

  @Input()
  endPoint: string;

  @Input()
  onPull: any;

  @Input()
  width = '50%';

  @Input()
  height = '300px';

  callback = (chart) => {
    if (chart) {
      this.chart.puller.subscribe((initialized) => {
        if (initialized && !this.pending) {
          this.pending = true;
          this.service.get(this.endPoint).subscribe((data) => {
            this.onPull(data, chart);
            this.pending = false;
          }, () =>  {
            this.pending = false;
          });
        }
      });
    }
  }

  constructor(private service: DataService) { }

  ngOnInit() {
    this.chart = new ChartsOption(this.series, this.title, this.type);
  }

  setMyStyle() {
    const styles = {
      'width': this.width,
      'height': this.height,
      'display': 'inline-block'
    };
    return styles;
  }

}

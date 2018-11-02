import { Component, OnInit, Input } from '@angular/core';

@Component({
  selector: 'app-indicator',
  templateUrl: './indicator.component.html',
  styleUrls: ['./indicator.component.css']
})
export class IndicatorComponent implements OnInit {

  @Input()
  type: string = "string";

  @Input()
  value: string = "undefined";

  @Input()
  tile: any;

  duration: number;

  constructor() { }

  ngOnInit() {
  }

  colorizeAndFormat(status) {
    if (status !== 'Contact lost') {
      if (this.tile.color !== 'lightgreen') {
        setTimeout(() => {
          this.tile.color = 'lightgreen';
        });
      }
      // console.log(this.tile.text, status);
    } else {
      if (this.tile.color !== 'crimson') {
        setTimeout(() => {
          this.tile.color = 'crimson';
        });
      }
    }
    if (this.type === "status") {
      return status !== 'Contact lost' ? 'Up' : status;
    } else if (this.type === 'number') {
      status = this.formatNumber(status);
    }

    return status;
  }

  formatNumber(number) {
    let prefix = this.tile.prefix ? this.tile.prefix : '';
    let suffix = this.tile.suffix ? this.tile.suffix : '';

    return `${prefix}${number}${suffix}`;
  }

  updateDuration() {
    if (this.tile.request.duration) {
      this.duration = this.tile.request.duration
    }
    return this.duration;
  }
}

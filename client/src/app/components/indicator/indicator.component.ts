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

  constructor() { }

  ngOnInit() {
  }

  formatStatus(status) {
    if (status) {
      if (this.tile.color !== 'lightgreen' ) {
        setTimeout(() => {
          this.tile.color = 'lightgreen';
        });
      }
      return 'OK';
    }
    if (this.tile.color !== 'crimson' ) {
      setTimeout(() => {
        this.tile.color = 'crimson';
      });
    }
    return 'KO';
  }

  formatNumber(number) {
    let prefix = this.tile.prefix ? this.tile.prefix : '';
    let suffix = this.tile.suffix ? this.tile.suffix : '';

    return `${prefix}${number}${suffix}`;
  }
}

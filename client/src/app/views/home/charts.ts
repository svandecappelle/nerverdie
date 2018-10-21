import * as Highcharts from 'highcharts';

import { BehaviorSubject } from 'rxjs';

const splineChart = {
    chart: {
        type: 'spline',
        animation: false,
        // animation: Highcharts.svg, // don't animate in old IE
        marginRight: 10,
        events: {
            load: function () {}
        }
    },

    time: {
        useUTC: false
    },
    xAxis: {
        type: 'datetime',
        tickPixelInterval: 150
    },
    yAxis: {
        title: {
            text: 'Value'
        },
        plotLines: [{
            value: 0,
            width: 1,
            color: '#808080'
        }]
    },
    tooltip: {
        headerFormat: '<b>{series.name}</b><br/>',
        pointFormat: '{point.x:%Y-%m-%d %H:%M:%S}<br/>{point.y:.2f}'
    },
    legend: {
        enabled: true
    },
    exporting: {
        enabled: true
    }
};

export class ChartsOption {

    options: any;
    private puller: BehaviorSubject<any> = new BehaviorSubject<any>(false);
    private chart: any;

    constructor(init: any, title: string) {
        this.options = splineChart;
        this.options.title = {
            text: title
        };
        this.options.series = init;
        const that = this;
        this.options.chart.events.load = function () {
            that.chart = this;
            that.onLoad();
        };
    }

    public onLoad() {
        setInterval(() => {
            this.puller.next(true);
        }, 1000);
    }

    public get pull() {
        return this.puller;
    }

    public get series() {
        return this.chart.series;
    }
}

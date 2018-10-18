Object.byString = function(o, s) {
    s = s.replace(/\[(\w+)\]/g, '.$1'); // convert indexes to properties
    s = s.replace(/^\./, '');           // strip a leading dot
    var a = s.split('.');
    for (var i = 0, n = a.length; i < n; ++i) {
        var k = a[i];
        if (k in o) {
            o = o[k];
        } else {
            return;
        }
    }
    return o;
}

function MetricParser (value) {
    this.value = value;
}

MetricParser.prototype.parse = function (parsing) {
    if (parsing.lastIndexOf(',') !== -1) {
        var values = [];
        parsing.split(',').forEach(element => {
            values.push(Object.byString(this.value, element))
        });
        return values;
    }

    return Object.byString(this.value, parsing);
}


function Formatter (formatterType, value) {
    this.value = value;
    switch (formatterType) {
        case 'time':
            this.formatter = {
                format: function formatDuration(value, style){
                    return moment.duration(value).format(style);
                }
            }
            break;
        case 'bytes':
            this.formatter = {
                format: function formatBytes(bytes, decimals) {
                    if(bytes == 0) return '0 Bytes';
                    var k = 1024,
                        dm = decimals || 2,
                        sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'],
                        i = Math.floor(Math.log(bytes) / Math.log(k));
                    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
                }
            }
            break;
        case 'boolean':
            this.formatter = {
                format: function formatBoolean(value, opts) {
                    if (value) {
                        return opts.true;
                    }
                    return opts.false;
                } 
            }
            break;
    }
}

Formatter.prototype.format = function (opts) {
    return this.formatter.format(this.value, opts);
}


function Chart (id) {
    this.id = id;
    this.countCalls = 0;
    this.duration = 1250;
    this.maxTicksCount = 50;
    this.animationDuration = 0;
};

Chart.prototype.build = function build (series, route, options) {
    this._series = series;
    this.route = route;
    this.title = options.title;

    $("#" + this.id + '-refresh').click(() => {
        this.tick(false);
    });

    var groups = undefined;
    if (options.stack) {
        groups = [this.series()];
    }

    var type = 'spline';
    if (options.type){
        type = options.type
    }

    this.chart = c3.generate({
        bindto: '#' + this.id,
        point: {
            show: false
        },
        data: {
            url: this.route,
            mimeType: 'json',
            keys: {
                x: 'date',
                value: this.series()
            },
            xFormat: '%Y-%m-%d %H:%M:%S',
            type: type,
            groups: groups
        },
        axis: {
            x: {
                type: 'timeseries',
                tick: {
                    fit: true,
                    format: '%Hh %Mm %Ss'
                }
            }
        }
    });
    this.tick();
}

Chart.prototype.tick = function render (autorefresh) {
    setInterval( () => {
        $.get(this.route, (data) => {
            var serie = this.series()[0];
            
            if (!this.to){
                this.to = this.chart.xs()[serie][0];     
            }
            
            if (this.countCalls > this.maxTicksCount){
                this.to = this.chart.xs()[serie][this.countCalls - this.maxTicksCount];
            }
            
            this.chart.flow({
                json: data,
                keys: {
                    x: 'date',
                    value: this.series()
                },
                xFormat: '%Y-%m-%d %H:%M:%S',
                lenght: 1,
                to: this.to,
                //duration: this.animationDuration,
                done: () => {
                    this.countCalls += 1;
                    /*if (autorefresh == undefined || autorefresh){
                        this.tick();
                    }*/
                }
            });
        });
    }, this.duration);
}

Chart.prototype.series = function () {
    return this._series.split(',');
}

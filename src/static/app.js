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
    this.duration = 2000;
    this.maxTicksCount = 50;
    this.animationDuration = 1000;
};

Chart.prototype.build = function build (value) {
    this.value = value;
    
    $('#' + this.id).css({
        "background-color": "#FFF",
        "box-shadow": "1px 1px 3px rgba(0,0,0,0.5)",
        "border-radius": "2px"
    });
    this.chart = c3.generate({
        bindto: '#' + this.id,
        data: {
            x: 'x',
            columns: [
                ['cpu0'],
                ['cpu1']
            ],
            types: {
                'cpu0': 'area-spline',
                'cpu1': 'area-spline',
                'cpu2': 'area-spline',
                'cpu3': 'area-spline'
            },
            groups: [['cpu0', 'cpu1', 'cpu2', 'cpu3']]
        },
        axis: {
            x: {
                type: 'timeseries',
                tick: {
                    format: '%Hh %Mm %Ss'
                }
            }
        }
    });
    this.tick();
}

Chart.prototype.tick = function render() {
    this.countCalls += 1;
    $.get('/api/cpu/load', (data) => {

        var current_data = [];
        current_data.push(['x', moment()]);
        this.series().forEach((element, index) => {
            var parser = new MetricParser(data);
            var parsed_value = parser.parse(this.value);
            current_data.push(['cpu' + index, parsed_value[index]]);
        });

        var to = 0;
        if (this.countCalls > this.maxTicksCount){
            to = this.countCalls - this.maxTicksCount;
        }
        this.chart.flow({
            columns: current_data,
            lenght: 1,
            to: to,
            duration: this.animationDuration,
            done: () => {
                setTimeout( () => {
                    this.tick();
                }, this.duration);
            }
        });
    });
    
}

Chart.prototype.series = function () {
    return this.value.split(',');
}

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
    this.data = [];
};

Chart.prototype.build = function build (value) {
    this.value = value;
    this.timeoutId = 0;
    
    this.margin = {top: 20, right: 20, bottom: 30, left: 20};
    this.width = $("#" + this.id).outerWidth() - this.margin.left - this.margin.right;
    this.height = 320 - this.margin.top - this.margin.bottom;
    
    this.parseDate = d3.timeParse("%H:%M:%S");
    
    this.xcenter =  this.width / 2;

    // Start
    this.update();
}

Chart.prototype.render = function render() {
    var that = this;

    d3.select("#" + this.id + " > svg")
        .remove();

    var svg = d3.select("#" + this.id).append("svg")
        .attr("width", this.width + this.margin.left + this.margin.right)
        .attr("height", this.height + this.margin.top + this.margin.bottom + 40)
        .append("g")
        .attr("transform", "translate(" + this.margin.left + "," + this.margin.top + ")");

    d3.json('/api/cpu/load', function(d){
        that.callRender(svg, {
            date: new Date(),
            cpu:  Object.byString(d, that.value)
        });
        
        that.timeoutId = setTimeout(function(){
            that.update();
        }, 2000);
        
    });
}

Chart.prototype.callRender = function callRender (chart, data) {
    var x = d3.scaleTime()
        .rangeRound([0, this.width]);
    
    var y = d3.scaleLinear()
        .rangeRound([this.height, 0]);
    
    var line = d3.line()
        .x(function(d) { return x(d.date); })
        .y(function(d) { return y(d.cpu); });

    this.data.push(data);

    x.domain(d3.extent(this.data, function(d) { return d.date; }));
    y.domain(d3.extent(this.data, function(d) { return d.cpu; }));
    
    g = chart.append("g").attr("transform", "translate(" + this.margin.left + "," + this.margin.top + ")");
    g.append("g")
        .attr("transform", "translate(0," + this.height + ")")
        .call(d3.axisBottom(x))
        .attr("class", "chart-axis")
        .select(".domain")
        .remove();

    g.append("g")
        .call(d3.axisLeft(y))
        .attr("class", "chart-axis")
        .append("text")
            .attr("transform", "rotate(-90)")
            .attr("y", 6)
            .attr("dy", "0.71em")
            .attr("text-anchor", "end")
            .text("Value");

    g.append("path")
        .datum(this.data)
        .attr("class", "chart")
        .attr("fill", "none")
        .attr("stroke-linejoin", "round")
        .attr("stroke-linecap", "round")
        .attr("stroke-width", 1.5)
        .attr("d", line);
}

Chart.prototype.update =  function update() {
    this.render();
    var that = this;
}
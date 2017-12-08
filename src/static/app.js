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
            this.formatter = moment.duration(value);
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
    if (this.formatter.humanize) {
        return this.formatter.humanize();
    } else {
        console.log(opts);
        return this.formatter.format(this.value, opts);
    }
}
import {
  MIN_WINDOW,
  appendPoints,
  buildChartConfig,
  generateEmptyData,
  windowFor,
  xBounds,
} from './charts';

describe('buildChartConfig', () => {
  it('applies title and series', () => {
    const config = buildChartConfig([{ name: 'Used', data: [{ x: 1, y: 2 }] }], 'Memory', 'spline');

    expect(config.type).toBe('line');
    expect(config.options?.plugins?.title?.text).toBe('Memory');
    expect(config.data.datasets).toHaveLength(1);
    expect(config.data.datasets[0].label).toBe('Used');
    expect(config.data.datasets[0].data).toEqual([{ x: 1, y: 2 }]);
  });

  it('maps the chart types to curve, fill and stacking options', () => {
    const series = [
      { name: 'a', data: [] },
      { name: 'b', data: [] },
    ];
    const spline = buildChartConfig(series, '', 'spline');
    expect(spline.data.datasets[0].tension).toBeGreaterThan(0);
    expect(spline.data.datasets[0].fill).toBe(false);

    const areaspline = buildChartConfig(series, '', 'areaspline');
    expect(areaspline.data.datasets[0].fill).toBe('origin');

    const area = buildChartConfig(series, '', 'area');
    expect(area.data.datasets.map((d) => d.fill)).toEqual(['origin', '-1']);
    expect(area.options?.scales?.['y']?.stacked).toBe(true);
    expect(area.data.datasets[0].tension).toBe(0);
  });

  it('does not share point objects with the input series', () => {
    const data = [{ x: 1, y: 2 }];
    const config = buildChartConfig([{ name: 'a', data }], '', 'line');
    config.data.datasets[0].data[0].y = 5;
    expect(data[0].y).toBe(2);
  });

  it('sets the x axis bounds to the data, not to rounded values', () => {
    const config = buildChartConfig(
      [{ name: 'a', data: [{ x: 1_764_000_000_123, y: 1 }, { x: 1_764_000_600_456, y: 2 }] }],
      '',
      'line',
    );
    expect(config.options?.scales?.['x']?.min).toBe(1_764_000_000_123);
    expect(config.options?.scales?.['x']?.max).toBe(1_764_000_600_456);
  });
});

describe('appendPoints', () => {
  it('appends one point per series and drops the points older than the window', () => {
    const datasets = [
      { data: [{ x: 0, y: 1 }, { x: 5, y: 2 }] },
      { data: [{ x: 0, y: 3 }, { x: 5, y: 4 }] },
    ];
    appendPoints(datasets, 12, [10, 20], 10);
    expect(datasets[0].data).toEqual([{ x: 5, y: 2 }, { x: 12, y: 10 }]);
    expect(datasets[1].data).toEqual([{ x: 5, y: 4 }, { x: 12, y: 20 }]);
  });

  it('lets a short series grow until it fills the window', () => {
    const datasets = [{ data: [{ x: 0, y: 1 }] }];
    appendPoints(datasets, 3, [2], 10);
    appendPoints(datasets, 6, [3], 10);
    expect(datasets[0].data.map((p) => p.x)).toEqual([0, 3, 6]);
  });

  it('draws a gap when values are missing (contact lost)', () => {
    const datasets = [{ data: [{ x: 1, y: 1 }] }, { data: [{ x: 1, y: 1 }] }];
    appendPoints(datasets, 2, []);
    expect(datasets.map((d) => d.data.at(-1))).toEqual([
      { x: 2, y: null },
      { x: 2, y: null },
    ]);
  });
});

describe('xBounds and windowFor', () => {
  it('returns the extreme x values of all series', () => {
    expect(xBounds([{ data: [{ x: 5, y: 0 }] }, { data: [{ x: 2, y: 0 }, { x: 9, y: 0 }] }])).toEqual({
      min: 2,
      max: 9,
    });
    expect(xBounds([{ data: [] }])).toBeUndefined();
  });

  it('keeps at least MIN_WINDOW on screen, more when the history is longer', () => {
    expect(windowFor([{ name: 'a', data: [{ x: 0, y: 0 }] }])).toBe(MIN_WINDOW);
    const hour = 60 * 60 * 1000;
    expect(windowFor([{ name: 'a', data: [{ x: 0, y: 0 }, { x: hour, y: 0 }] }])).toBe(hour);
  });
});

describe('generateEmptyData', () => {
  it('returns one zero point per second', () => {
    const data = generateEmptyData(1, 0);
    expect(data).toHaveLength(61);
    expect(data.every((p) => p.y === 0)).toBe(true);
    expect(data[1].x - data[0].x).toBe(1000);
  });
});

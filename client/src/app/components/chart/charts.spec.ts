import { buildChartConfig, historyToSeries, xBounds } from './charts';

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

describe('xBounds', () => {
  it('returns the extreme x values of all series', () => {
    expect(xBounds([{ data: [{ x: 5, y: 0 }] }, { data: [{ x: 2, y: 0 }, { x: 9, y: 0 }] }])).toEqual({
      min: 2,
      max: 9,
    });
    expect(xBounds([{ data: [] }])).toBeUndefined();
  });
});

describe('historyToSeries', () => {
  const at = (time: string) => new Date(`2026-11-24T${time}`).getTime();

  it('builds one sorted series per core', () => {
    const series = historyToSeries(
      [
        { date: '2026-11-24 10:00:03', cpu0: 30, cpu1: 40 },
        { date: '2026-11-24 10:00:00', cpu0: 10, cpu1: 20 },
      ],
      ['cpu0', 'cpu1'],
    );
    expect(series).toEqual([
      [{ x: at('10:00:00'), y: 10 }, { x: at('10:00:03'), y: 30 }],
      [{ x: at('10:00:00'), y: 20 }, { x: at('10:00:03'), y: 40 }],
    ]);
  });

  it('draws a gap where the collection stopped, and for missing values', () => {
    const [cpu0] = historyToSeries(
      [
        { date: '2026-11-24 10:00:00', cpu0: 10 },
        { date: '2026-11-24 10:05:00', cpu0: null },
        { date: '2026-11-24 10:05:03', cpu0: 30 },
      ],
      ['cpu0'],
    );
    expect(cpu0.map((p) => p.y)).toEqual([10, null, null, 30]);
    expect(cpu0.map((p) => p.x)).toEqual([...cpu0.map((p) => p.x)].sort((a, b) => a - b));
  });

  it('uses the given gap for averaged (bucketed) histories', () => {
    const [cpu0] = historyToSeries(
      [
        { date: '2026-11-24 10:00:00', cpu0: 10 },
        { date: '2026-11-24 10:01:00', cpu0: 20 },
      ],
      ['cpu0'],
      150_000,
    );
    expect(cpu0.map((p) => p.y)).toEqual([10, 20]);
  });

  it('ignores entries without a valid date', () => {
    expect(historyToSeries([{ date: 'nope', cpu0: 1 }], ['cpu0'])).toEqual([[]]);
  });
});

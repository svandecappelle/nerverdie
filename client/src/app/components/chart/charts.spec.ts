import { buildChartOptions, generateEmptyData } from './charts';

describe('buildChartOptions', () => {
  it('applies title, chart type and series', () => {
    const options = buildChartOptions(
      [{ name: 'Used', data: [{ x: 1, y: 2 }] }],
      'Memory',
      'spline',
    );

    expect(options.title?.text).toBe('Memory');
    expect(options.chart?.type).toBe('spline');
    expect(options.series).toEqual([{ name: 'Used', data: [{ x: 1, y: 2 }], type: 'spline' }]);
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

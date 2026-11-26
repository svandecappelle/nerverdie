import { OVERALL_KEY, cpuKeys, cpuLegends, withOverallLoad } from './cpu-series';

const SAMPLES = [
  { date: '2026-11-25 10:00:00', cpu0: 10, cpu1: 30, cpu10: 50 },
  { date: '2026-11-25 10:00:03', cpu0: 20, cpu1: null, cpu10: 40 },
  { date: '2026-11-25 10:00:06', cpu0: null, cpu1: null, cpu10: null },
];

describe('cpu series', () => {
  it('lists the cores in their order', () => {
    expect(cpuKeys(SAMPLES)).toEqual(['cpu0', 'cpu1', 'cpu10']);
  });

  it('computes the overall load as the mean of the cores with a value', () => {
    expect(withOverallLoad(SAMPLES).map((sample) => sample[OVERALL_KEY])).toEqual([30, 30, null]);
    // The samples given are left untouched.
    expect(OVERALL_KEY in SAMPLES[0]).toBe(false);
  });

  it('names one series per core, or the overall one', () => {
    expect(cpuLegends(SAMPLES, 'cores')).toEqual({
      cpu0: 'Cpu load 0',
      cpu1: 'Cpu load 1',
      cpu10: 'Cpu load 10',
    });
    expect(cpuLegends(SAMPLES, 'overall')).toEqual({ [OVERALL_KEY]: 'Overall load' });
  });
});

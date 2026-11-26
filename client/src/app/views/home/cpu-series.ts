/** CPU chart: one line per core, or the overall load (mean of the cores). */
export type CpuView = 'cores' | 'overall';

export const CPU_VIEWS: CpuView[] = ['cores', 'overall'];
export const CPU_VIEW_LABELS: Record<CpuView, string> = { cores: 'Per core', overall: 'Overall' };

/** Key of the overall load added to the samples. */
export const OVERALL_KEY = 'overall';

type Sample = Record<string, number | string | null>;

/** CPU keys found in the samples, in core order (cpu0, cpu1, ..., cpu10). */
export function cpuKeys(samples: Sample[]): string[] {
  const keys = new Set<string>();
  samples.forEach((sample) => Object.keys(sample).forEach((key) => /^cpu\d+$/.test(key) && keys.add(key)));
  return [...keys].sort((a, b) => Number(a.slice(3)) - Number(b.slice(3)));
}

/**
 * Adds to each sample its overall load: the mean of its cores, like the
 * system-wide CPU percent. Cores without a value are left out; a sample
 * without any core value gets null (drawn as a gap).
 */
export function withOverallLoad(samples: Sample[], keys = cpuKeys(samples)): Sample[] {
  return samples.map((sample) => {
    const values = keys.map((key) => sample[key]).filter((value): value is number => typeof value === 'number');
    const overall = values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : null;
    return { ...sample, [OVERALL_KEY]: overall };
  });
}

/** Legend of each CPU series for a view: sample key -> name. */
export function cpuLegends(samples: Sample[], view: CpuView): Record<string, string> {
  if (view === 'overall') {
    return { [OVERALL_KEY]: 'Overall load' };
  }
  return Object.fromEntries(cpuKeys(samples).map((key) => [key, `Cpu load ${key.slice(3)}`]));
}

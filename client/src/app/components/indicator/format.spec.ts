import { humanToBytes, humanizeDuration } from './format';

describe('humanizeDuration', () => {
  it('uses the largest sensible unit', () => {
    expect(humanizeDuration(10)).toBe('10 seconds');
    expect(humanizeDuration(90)).toBe('2 minutes');
    expect(humanizeDuration(3 * 3600)).toBe('3 hours');
    expect(humanizeDuration(3 * 86400)).toBe('3 days');
    expect(humanizeDuration(400 * 86400)).toBe('1 year');
  });

  it('never shows zero', () => {
    expect(humanizeDuration(0)).toBe('1 second');
  });
});

describe('humanToBytes', () => {
  it('parses the bytes2human format of the server', () => {
    expect(humanToBytes('512.00B')).toBe(512);
    expect(humanToBytes('2.00K')).toBe(2048);
    expect(humanToBytes('1.50M')).toBe(1.5 * 1024 * 1024);
    expect(humanToBytes('1.00G')).toBe(1024 ** 3);
  });

  it('passes numbers through and rejects garbage', () => {
    expect(humanToBytes(42)).toBe(42);
    expect(humanToBytes('n/a')).toBeNaN();
  });
});

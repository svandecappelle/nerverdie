import { ComponentFixture, TestBed } from '@angular/core/testing';

import { CONTACT_LOST, IndicatorComponent, IndicatorTile } from './indicator.component';

describe('IndicatorComponent', () => {
  let fixture: ComponentFixture<IndicatorComponent>;

  async function render(tile: IndicatorTile): Promise<string> {
    fixture.componentRef.setInput('tile', tile);
    await fixture.whenStable();
    return (fixture.nativeElement as HTMLElement).textContent ?? '';
  }

  beforeEach(() => {
    fixture = TestBed.createComponent(IndicatorComponent);
  });

  it('shows "Up" for a reachable status tile', async () => {
    const text = await render({ text: 'status', type: 'status', value: ['cpu'], duration: 0.02 });
    expect(text).toContain('status');
    expect(text).toContain('Up');
    expect(text).toContain('last request duration 0.02secs');
  });

  it('humanizes an uptime given in milliseconds', async () => {
    expect(await render({ text: 'uptime', type: 'duration', value: 3 * 86400 * 1000 })).toContain(
      '3 days',
    );
  });

  it('shows prefix and suffix around numbers', async () => {
    expect(
      await render({ text: 'load', type: 'number', value: 1234.5, prefix: '~', suffix: '%' }),
    ).toContain('~1,234.5%');
  });

  it('shows the contact lost message', async () => {
    const text = await render({ text: 'cpu', type: 'string', value: CONTACT_LOST });
    expect(text).toContain(CONTACT_LOST);
    expect(text).not.toContain('last request duration');
  });
});

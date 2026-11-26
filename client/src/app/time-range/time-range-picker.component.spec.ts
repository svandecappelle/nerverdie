import { Component } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { Router, provideRouter } from '@angular/router';

import { TimeRangePickerComponent } from './time-range-picker.component';
import { TimeRangeService } from './time-range.service';

@Component({
  imports: [TimeRangePickerComponent],
  providers: [TimeRangeService],
  template: '<app-time-range-picker />',
})
class HostComponent {}

describe('TimeRangePickerComponent', () => {
  async function render(url = '/') {
    TestBed.configureTestingModule({
      providers: [provideRouter([{ path: '**', component: HostComponent }])],
    });
    await TestBed.inject(Router).navigateByUrl(url);
    const fixture = TestBed.createComponent(HostComponent);
    await fixture.whenStable();
    const service = fixture.debugElement.children[0].injector.get(TimeRangeService);
    return { fixture, service, el: fixture.nativeElement as HTMLElement };
  }

  const panel = () => document.querySelector<HTMLElement>('.panel-popup');
  const button = (root: ParentNode, text: string) =>
    [...root.querySelectorAll<HTMLButtonElement>('button')].find((b) => b.textContent?.trim().startsWith(text));

  afterEach(() => localStorage.clear());

  it('shows the last hour by default', async () => {
    const { el, service } = await render();
    expect(el.querySelector('.picker')?.textContent).toContain('Last hour');
    expect(service.range()).toEqual({ from: 'now-1h', to: 'now' });
    expect(service.endsNow()).toBe(true);
  });

  it('reads the range and refresh from the URL', async () => {
    const { el, service } = await render('/?from=now-6h&to=now&refresh=30s');
    expect(service.range()).toEqual({ from: 'now-6h', to: 'now' });
    expect(service.refresh()).toBe('30s');
    expect(el.querySelector('.interval')?.textContent).toContain('30s');
  });

  it('ignores an invalid range in the URL', async () => {
    const { service } = await render('/?from=garbage&to=now');
    expect(service.range()).toEqual({ from: 'now-1h', to: 'now' });
  });

  it('applies a quick range and writes it in the URL', async () => {
    const { fixture, el, service } = await render();
    el.querySelector<HTMLButtonElement>('.picker')!.click();
    await fixture.whenStable();
    button(panel()!, 'Last 15 minutes')!.click();
    await fixture.whenStable();

    expect(service.range()).toEqual({ from: 'now-15m', to: 'now' });
    expect(el.querySelector('.picker')?.textContent).toContain('Last 15 minutes');
    expect(TestBed.inject(Router).url).toContain('from=now-15m');
    expect(panel()).toBeNull();
  });

  it('validates the absolute range before applying it', async () => {
    const { fixture, el, service } = await render();
    el.querySelector<HTMLButtonElement>('.picker')!.click();
    await fixture.whenStable();
    const [from, to] = panel()!.querySelectorAll<HTMLInputElement>('form input');

    from.value = 'tomorrow';
    from.dispatchEvent(new Event('input'));
    button(panel()!, 'Apply time range')!.click();
    await fixture.whenStable();
    expect(panel()!.querySelector('[role=alert]')?.textContent).toContain('Invalid "From"');
    expect(service.range().from).toBe('now-1h');

    from.value = '2026-11-25 10:00:00';
    from.dispatchEvent(new Event('input'));
    to.value = '2026-11-25 11:00:00';
    to.dispatchEvent(new Event('input'));
    button(panel()!, 'Apply time range')!.click();
    await fixture.whenStable();
    expect(service.range()).toEqual({ from: '2026-11-25 10:00:00', to: '2026-11-25 11:00:00' });
    expect(service.recent()[0]).toEqual(service.range());
    expect(service.endsNow()).toBe(false);
  });

  it('filters the quick ranges', async () => {
    const { fixture, el } = await render();
    el.querySelector<HTMLButtonElement>('.picker')!.click();
    await fixture.whenStable();
    const search = panel()!.querySelector<HTMLInputElement>('input[aria-label="Search quick ranges"]')!;
    search.value = 'day';
    search.dispatchEvent(new Event('input'));
    await fixture.whenStable();
    const labels = [...panel()!.querySelectorAll('[aria-label="Quick ranges"] button')].map((b) => b.textContent?.trim());
    expect(labels).toEqual(['Last 2 days', 'Last 7 days', 'Last 30 days']);
  });

  it('zooms out and shifts the range', async () => {
    const { fixture, el, service } = await render('/?from=now-5m&to=now');
    el.querySelector<HTMLButtonElement>('[aria-label="Zoom out time range"]')!.click();
    await fixture.whenStable();
    expect(service.range()).toEqual({ from: 'now-10m', to: 'now' });

    el.querySelector<HTMLButtonElement>('[aria-label="Move time range backward"]')!.click();
    await fixture.whenStable();
    expect(service.endsNow()).toBe(false);
    expect(el.querySelector<HTMLButtonElement>('[aria-label="Move time range forward"]')!.disabled).toBe(false);
  });
});

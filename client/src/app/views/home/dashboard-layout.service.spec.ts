import { TestBed } from '@angular/core/testing';

import { DEFAULT_LAYOUT, DashboardLayoutService, sanitizeLayout } from './dashboard-layout.service';

describe('sanitizeLayout', () => {
  it('returns the default layout for nothing usable', () => {
    expect(sanitizeLayout(undefined)).toEqual(DEFAULT_LAYOUT);
    expect(sanitizeLayout('garbage')).toEqual(DEFAULT_LAYOUT);
    expect(sanitizeLayout({ panels: 'x', hiddenTiles: 3 })).toEqual(DEFAULT_LAYOUT);
  });

  it('drops unknown and duplicate panels, fixes bad values and appends missing panels', () => {
    const layout = sanitizeLayout({
      panels: [
        { id: 'network', visible: false, width: 'half', height: 'large' },
        { id: 'disk', visible: true },
        { id: 'network', visible: true },
        { id: 'cpu', width: 'huge', height: 12 },
      ],
      hiddenTiles: ['Uptime', 4],
    });
    expect(layout).toEqual({
      panels: [
        { id: 'network', visible: false, width: 'half', height: 'large' },
        { id: 'cpu', visible: true, width: 'full', height: 'medium' },
        { id: 'memory', visible: true, width: 'full', height: 'medium' },
      ],
      hiddenTiles: ['Uptime'],
    });
  });
});

describe('DashboardLayoutService', () => {
  const service = () => TestBed.inject(DashboardLayoutService);
  const stored = () => JSON.parse(localStorage.getItem('neverdie.dashboard') ?? 'null');

  afterEach(() => localStorage.clear());

  it('starts with every tile and chart, full width', () => {
    expect(service().layout()).toEqual(DEFAULT_LAYOUT);
    expect(service().customized()).toBe(false);
  });

  it('reads the stored layout', () => {
    localStorage.setItem('neverdie.dashboard', JSON.stringify({ panels: [{ id: 'memory' }], hiddenTiles: ['Host'] }));
    expect(service().layout().panels.map((panel) => panel.id)).toEqual(['memory', 'cpu', 'network']);
    expect(service().isTileVisible('Host')).toBe(false);
  });

  it('survives an unreadable stored layout', () => {
    localStorage.setItem('neverdie.dashboard', '{not json');
    expect(service().layout()).toEqual(DEFAULT_LAYOUT);
  });

  it('updates, moves and hides panels, and keeps the result', () => {
    const layout = service();
    layout.updatePanel('memory', { width: 'half', height: 'small' });
    layout.updatePanel('cpu', { visible: false });
    layout.movePanel(2, 0);
    layout.movePanel(0, 5); // out of range: ignored

    expect(layout.layout().panels).toEqual([
      { id: 'network', visible: true, width: 'full', height: 'medium' },
      { id: 'cpu', visible: false, width: 'full', height: 'medium' },
      { id: 'memory', visible: true, width: 'half', height: 'small' },
    ]);
    expect(layout.visiblePanels().map((panel) => panel.id)).toEqual(['network', 'memory']);
    expect(layout.customized()).toBe(true);
    expect(stored()).toEqual(layout.layout());
  });

  it('hides and shows tiles', () => {
    const layout = service();
    layout.setTileVisible('Uptime', false);
    layout.setTileVisible('Uptime', false);
    expect(layout.layout().hiddenTiles).toEqual(['Uptime']);
    layout.setTileVisible('Uptime', true);
    expect(layout.isTileVisible('Uptime')).toBe(true);
  });

  it('resets to the default layout', () => {
    const layout = service();
    layout.updatePanel('cpu', { visible: false });
    layout.setTileVisible('Host', false);
    layout.reset();
    expect(layout.layout()).toEqual(DEFAULT_LAYOUT);
    expect(stored()).toEqual(DEFAULT_LAYOUT);
  });
});

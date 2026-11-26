import { Injectable, computed, signal } from '@angular/core';

import { CPU_VIEWS, CpuView } from './cpu-series';

export type PanelId = 'cpu' | 'memory' | 'network';
export type PanelWidth = 'full' | 'half';
export type PanelHeight = 'small' | 'medium' | 'large';

export interface PanelLayout {
  id: PanelId;
  visible: boolean;
  width: PanelWidth;
  height: PanelHeight;
}

/** Dashboard layout: chart panels in display order, the hidden status tiles and the CPU chart view. */
export interface DashboardLayout {
  panels: PanelLayout[];
  hiddenTiles: string[];
  cpuView: CpuView;
}

export const PANEL_IDS: PanelId[] = ['cpu', 'memory', 'network'];
export const PANEL_TITLES: Record<PanelId, string> = { cpu: 'CPU', memory: 'Memory', network: 'Network' };
export const PANEL_WIDTHS: PanelWidth[] = ['full', 'half'];
export const PANEL_HEIGHTS: PanelHeight[] = ['small', 'medium', 'large'];

/** Chart height (CSS) of each panel height. */
export const HEIGHT_PX: Record<PanelHeight, string> = { small: '200px', medium: '300px', large: '460px' };

export const DEFAULT_LAYOUT: DashboardLayout = {
  panels: PANEL_IDS.map((id) => ({ id, visible: true, width: 'full', height: 'medium' })),
  hiddenTiles: [],
  cpuView: 'cores',
};

const STORAGE_KEY = 'neverdie.dashboard';

/**
 * Keeps a stored layout usable: unknown panels and values are dropped,
 * panels missing from it (added by a newer version) are appended.
 */
export function sanitizeLayout(value: unknown): DashboardLayout {
  const layout = (value ?? {}) as Partial<DashboardLayout>;
  const panels: PanelLayout[] = [];
  for (const panel of Array.isArray(layout.panels) ? layout.panels : []) {
    if (!PANEL_IDS.includes(panel?.id) || panels.some((p) => p.id === panel.id)) {
      continue;
    }
    panels.push({
      id: panel.id,
      visible: panel.visible !== false,
      width: PANEL_WIDTHS.includes(panel.width) ? panel.width : 'full',
      height: PANEL_HEIGHTS.includes(panel.height) ? panel.height : 'medium',
    });
  }
  for (const panel of DEFAULT_LAYOUT.panels) {
    if (!panels.some((p) => p.id === panel.id)) {
      panels.push({ ...panel });
    }
  }
  const hiddenTiles = Array.isArray(layout.hiddenTiles)
    ? layout.hiddenTiles.filter((tile): tile is string => typeof tile === 'string')
    : [];
  const cpuView = CPU_VIEWS.includes(layout.cpuView as CpuView) ? (layout.cpuView as CpuView) : 'cores';
  return { panels, hiddenTiles, cpuView };
}

/** Layout of the dashboard chosen by the viewer, kept in the browser. */
@Injectable({ providedIn: 'root' })
export class DashboardLayoutService {
  readonly layout = signal<DashboardLayout>(this.load());
  readonly visiblePanels = computed(() => this.layout().panels.filter((panel) => panel.visible));
  /** Whether the layout differs from the default one. */
  readonly customized = computed(() => JSON.stringify(this.layout()) !== JSON.stringify(DEFAULT_LAYOUT));

  updatePanel(id: PanelId, patch: Partial<Omit<PanelLayout, 'id'>>): void {
    this.save({
      ...this.layout(),
      panels: this.layout().panels.map((panel) => (panel.id === id ? { ...panel, ...patch } : panel)),
    });
  }

  /** Moves a panel from one position to another (display order). */
  movePanel(from: number, to: number): void {
    const panels = [...this.layout().panels];
    if (from === to || from < 0 || to < 0 || from >= panels.length || to >= panels.length) {
      return;
    }
    const [panel] = panels.splice(from, 1);
    panels.splice(to, 0, panel);
    this.save({ ...this.layout(), panels });
  }

  setTileVisible(tile: string, visible: boolean): void {
    const hidden = this.layout().hiddenTiles.filter((t) => t !== tile);
    this.save({ ...this.layout(), hiddenTiles: visible ? hidden : [...hidden, tile] });
  }

  setCpuView(cpuView: CpuView): void {
    this.save({ ...this.layout(), cpuView });
  }

  isTileVisible(tile: string): boolean {
    return !this.layout().hiddenTiles.includes(tile);
  }

  reset(): void {
    this.save(sanitizeLayout(DEFAULT_LAYOUT));
  }

  private save(layout: DashboardLayout): void {
    this.layout.set(layout);
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(layout));
    } catch {
      // Storage unavailable (private mode...): the layout lasts for this page only.
    }
  }

  private load(): DashboardLayout {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      return sanitizeLayout(stored ? JSON.parse(stored) : DEFAULT_LAYOUT);
    } catch {
      return sanitizeLayout(DEFAULT_LAYOUT);
    }
  }
}

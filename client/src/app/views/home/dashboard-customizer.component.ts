import { CdkDrag, CdkDragDrop, CdkDragHandle, CdkDropList } from '@angular/cdk/drag-drop';
import { Component, inject, input, output } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatButtonToggleModule } from '@angular/material/button-toggle';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatIconModule } from '@angular/material/icon';
import { MatTooltipModule } from '@angular/material/tooltip';

import {
  DashboardLayoutService,
  PANEL_TITLES,
  PanelHeight,
  PanelId,
  PanelWidth,
} from './dashboard-layout.service';

/** Edit panel of the dashboard: tiles and charts shown, chart order and size. */
@Component({
  selector: 'app-dashboard-customizer',
  imports: [
    CdkDropList,
    CdkDrag,
    CdkDragHandle,
    MatButtonModule,
    MatButtonToggleModule,
    MatCheckboxModule,
    MatIconModule,
    MatTooltipModule,
  ],
  templateUrl: './dashboard-customizer.component.html',
  styleUrl: './dashboard-customizer.component.scss',
})
export class DashboardCustomizerComponent {
  protected readonly layout = inject(DashboardLayoutService);
  protected readonly titles = PANEL_TITLES;
  protected readonly widths: { value: PanelWidth; label: string }[] = [
    { value: 'half', label: 'Half' },
    { value: 'full', label: 'Full' },
  ];
  protected readonly heights: { value: PanelHeight; label: string; short: string }[] = [
    { value: 'small', label: 'Small', short: 'S' },
    { value: 'medium', label: 'Medium', short: 'M' },
    { value: 'large', label: 'Large', short: 'L' },
  ];

  /** Names of the status tiles. */
  readonly tiles = input.required<string[]>();
  readonly done = output<void>();

  protected drop(event: CdkDragDrop<unknown>): void {
    this.layout.movePanel(event.previousIndex, event.currentIndex);
  }

  protected setWidth(id: PanelId, width: PanelWidth): void {
    this.layout.updatePanel(id, { width });
  }

  protected setHeight(id: PanelId, height: PanelHeight): void {
    this.layout.updatePanel(id, { height });
  }
}

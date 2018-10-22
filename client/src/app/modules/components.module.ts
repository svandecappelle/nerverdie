import { BrowserModule } from '@angular/platform-browser';
import { NgModule } from '@angular/core';

import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { MaterialModule } from '../modules/material.module';
import { MomentModule } from 'ngx-moment';

import { HighchartsChartModule } from 'highcharts-angular';
import { AppRoutingModule } from './app-routing.module';

import { IndicatorComponent } from '../components/indicator/indicator.component';
import { ChartComponent } from '../components/chart/chart.component';
import { DataService } from '../services/data.service';


@NgModule({
  declarations: [
    IndicatorComponent,
    ChartComponent
  ],
  imports: [
    BrowserModule,
    BrowserAnimationsModule,
    FormsModule,
    ReactiveFormsModule,
    MaterialModule,
    HighchartsChartModule,
    MomentModule,
    AppRoutingModule
  ],
  exports: [
    IndicatorComponent,
    ChartComponent
  ],
  providers: [
    DataService
  ],
})
export class ComponentsModule { }

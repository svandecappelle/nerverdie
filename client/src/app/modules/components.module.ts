import { BrowserModule } from '@angular/platform-browser';
import { NgModule } from '@angular/core';

import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { MaterialModule } from '../modules/material.module';
import { MomentModule } from 'ngx-moment';

import { AppRoutingModule } from './app-routing.module';

import { IndicatorComponent } from '../components/indicator/indicator.component';

@NgModule({
  declarations: [
    IndicatorComponent
  ],
  imports: [
    BrowserModule,
    BrowserAnimationsModule,
    FormsModule,
    ReactiveFormsModule,
    MaterialModule,
    MomentModule,
    AppRoutingModule
  ],
  exports: [
    IndicatorComponent
  ],
  providers: [],
})
export class ComponentsModule { }

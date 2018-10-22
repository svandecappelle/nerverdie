import { BrowserModule } from '@angular/platform-browser';
import { NgModule } from '@angular/core';

import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { MaterialModule } from './modules/material.module';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';

import { HighchartsChartModule } from 'highcharts-angular'; 

import { AppComponent } from './app.component';
import { AppRoutingModule } from './modules/app-routing.module';
import { HttpClientModule } from '@angular/common/http';

import { HeaderComponent } from './components/header/header.component';
import { ContentComponent } from './components/content/content.component';

import { ViewsModule } from './modules/views.module';

import { AuthenticationService } from './services/authentication.service';
import { AlertService } from './services/alert.service';
import { DataService } from './services/data.service';

import { AuthGuard } from './guards/index';

@NgModule({
  declarations: [
    AppComponent,
    ContentComponent,
    HeaderComponent
  ],
  imports: [
    BrowserModule,
    BrowserAnimationsModule,
    MaterialModule,
    HighchartsChartModule,
    FormsModule,
    ReactiveFormsModule,
    AppRoutingModule,
    HttpClientModule,
    ViewsModule,
  ],
  providers: [
    AuthenticationService,
    AlertService,
    AuthGuard,
    DataService,
  ],
  bootstrap: [AppComponent]
})
export class AppModule { }

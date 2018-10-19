import { BrowserModule } from '@angular/platform-browser';
import { NgModule } from '@angular/core';

import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { MaterialModule } from './modules/material.module';

import { AppComponent } from './app.component';
import { AppRoutingModule } from './modules/app-routing.module';

import { HeaderComponent } from './components/header/header.component';
import { ContentComponent } from './components/content/content.component';

import { ViewsModule } from './modules/views.module';
import { ComponentsModule } from './modules/components.module';

@NgModule({
  declarations: [
    AppComponent,
    ContentComponent,
    HeaderComponent,
  ],
  imports: [
    BrowserModule,
    BrowserAnimationsModule,
    MaterialModule,
    ViewsModule,
    AppRoutingModule
  ],
  providers: [],
  bootstrap: [AppComponent]
})
export class AppModule { }

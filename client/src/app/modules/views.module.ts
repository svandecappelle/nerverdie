import { BrowserModule } from '@angular/platform-browser';
import { NgModule } from '@angular/core';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';

import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { MaterialModule } from '../modules/material.module';

import { HomeComponent } from '../views/home/home.component';
import { LoginComponent } from '../views/login/login.component';

import { ComponentsModule } from './components.module';
import { AppRoutingModule } from './app-routing.module';

@NgModule({
  declarations: [
    LoginComponent,
    HomeComponent,
  ],
  imports: [
    BrowserModule,
    BrowserAnimationsModule,
    FormsModule,
    ReactiveFormsModule,
    MaterialModule,
    ComponentsModule,
    AppRoutingModule
  ],
  providers: [],
})
export class ViewsModule { }

import { BrowserModule } from '@angular/platform-browser';
import { NgModule } from '@angular/core';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';

import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { MaterialModule } from '../modules/material.module';

import { HomeComponent } from '../views/home/home.component';
import { LoginComponent } from '../views/login/login.component';

import { ComponentsModule } from './components.module';
import { AppRoutingModule } from './app-routing.module';

import { AuthenticationService } from '../services/authentication.service'
import { AlertService } from '../services/alert.service'
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
  providers: [
    AuthenticationService,
    AlertService,
  ],
})
export class ViewsModule { }

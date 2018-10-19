import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule, Routes } from '@angular/router';

import { AuthGuard } from '../guards/auth.guard';
import { LoginComponent } from '../views/login/login.component';
import { HomeComponent } from '../views/home/home.component';

const routes: Routes = [
  { path: '', component: HomeComponent, canActivate: [AuthGuard] },
  // { path: 'install', component: InstallComponent },
  // { path: 'upgrade', component: UpgradeComponent, canActivate: [AuthGuard] },

  // { path: 'admin', component: AdminComponent, canActivate: [AuthGuard] },

  { path: 'login', component: LoginComponent },
  // { path: 'register', component: RegisterComponent },
];

@NgModule({
  imports: [
    CommonModule,
    RouterModule.forRoot(routes)
  ],
  declarations: [],
  exports: [ RouterModule ]
})
export class AppRoutingModule { }

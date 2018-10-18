import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule, Routes } from '@angular/router';

import { HomeComponent } from '../home/home.component';

const routes: Routes = [
  { path: '', component: HomeComponent},
  // { path: 'install', component: InstallComponent },
  // { path: 'upgrade', component: UpgradeComponent, canActivate: [AuthGuard] },

  // { path: 'admin', component: AdminComponent, canActivate: [AuthGuard] },

  // { path: 'login', component: LoginComponent },
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

import { Component, OnInit } from '@angular/core';
// import { AuthenticationService } from './../services/authentication.service';

// import { Store, Action, select } from '@ngrx/store';

@Component({
  selector: 'app-header',
  templateUrl: './header.component.html',
  styleUrls: ['./header.component.scss']
})
export class HeaderComponent implements OnInit {
  // isLoggedIn$: Observable<boolean>;

  constructor(
    // private authService: AuthenticationService, 
    // private store: Store<IAppState>
    ) { }

  ngOnInit() {
    // this.isLoggedIn$ = this.authService.isLoggedIn();
  }

  onLogout() {
    // this.authService.logout();
  }

}

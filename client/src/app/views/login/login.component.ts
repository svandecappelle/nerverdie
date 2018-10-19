import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { Router, ActivatedRoute } from '@angular/router';

import { FormGroup, FormBuilder, Validators } from '@angular/forms';
import { AlertService, AuthenticationService } from '../../services/index';
// import { InstallService } from '../install/install.service';

@Component({
  selector: 'app-login',
  templateUrl: './login.component.html',
  styleUrls: ['./login.component.scss']
})
export class LoginComponent implements OnInit {
    form: FormGroup;
    private formSubmitAttempt: boolean;
    private loginInProgress: boolean;

    constructor(
      private ref: ChangeDetectorRef,
      private fb: FormBuilder,
      private authService: AuthenticationService,
      // private installService: InstallService,
      private router: Router
    ) {}

    ngOnInit() {
      /*this.installService.check().subscribe((result) => {
        console.log(result);
        if (!result.version) {
          this.router.navigate(['/install']);
        }
      });
      */
      this.form = this.fb.group({
        userName: ['', Validators.required],
        password: ['', Validators.required]
      });
    }

    isFieldInvalid(field: string) {
      this.loginInProgress = false;
      return (
        (!this.form.get(field).valid && this.form.get(field).touched) ||
        (this.form.get(field).untouched && this.formSubmitAttempt)
      );
    }

    onSubmit() {
      this.loginInProgress = true;
      this.ref.markForCheck();
      if (this.form.valid) {
        this.authService.login(this.form.value.userName, this.form.value.password);
        this.loginInProgress = false;
      }
      this.formSubmitAttempt = true;
    }
  }


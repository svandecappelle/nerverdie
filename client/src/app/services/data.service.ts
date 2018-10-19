import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Router } from '@angular/router';

import { BehaviorSubject } from 'rxjs';
import { Observable } from 'rxjs';
@Injectable({
  providedIn: 'root'
})
export class DataService {

  private data = new BehaviorSubject<any>(undefined); // {1}

  constructor(private http: HttpClient) {
  }

  get(dataName: any): Observable<any> {
    return this.http.get(`/api/${dataName}`);
  }
}

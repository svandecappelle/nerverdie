import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';

import { User } from '../models/user';

@Injectable({ providedIn: 'root' })
export class UserService {
  private readonly http = inject(HttpClient);

  isConnected() {
    return this.http.get('/api/auth');
  }

  getAll() {
    return this.http.get<User[]>('/api/users');
  }

  getById(id: string) {
    return this.http.get<User>(`/api/users/${id}`);
  }

  create(user: User) {
    return this.http.post('/api/users', user);
  }

  update(user: User) {
    return this.http.put(`/api/users/${user.id}`, user);
  }

  delete(id: string) {
    return this.http.delete(`/api/users/${id}`);
  }
}

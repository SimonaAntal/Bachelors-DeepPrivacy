import { TestBed } from '@angular/core/testing';

import { VaultService } from './vault';

describe('VaultService', () => {
  let service: VaultService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(VaultService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});

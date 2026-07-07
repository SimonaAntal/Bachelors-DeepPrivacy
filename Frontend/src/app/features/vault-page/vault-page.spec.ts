import { ComponentFixture, TestBed } from '@angular/core/testing';

import { VaultPage } from './vault-page';

describe('VaultPage', () => {
  let component: VaultPage;
  let fixture: ComponentFixture<VaultPage>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [VaultPage]
    })
    .compileComponents();

    fixture = TestBed.createComponent(VaultPage);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});

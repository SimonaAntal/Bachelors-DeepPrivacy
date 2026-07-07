import { ComponentFixture, TestBed } from '@angular/core/testing';

import { EncryptPage } from './encrypt-page';

describe('EncryptPage', () => {
  let component: EncryptPage;
  let fixture: ComponentFixture<EncryptPage>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EncryptPage]
    })
    .compileComponents();

    fixture = TestBed.createComponent(EncryptPage);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});

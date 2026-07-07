import json
import math
import random
import time

import torch
import torch.nn as nn
import torch.nn.functional as F
import kornia.augmentation as K
from torch.utils.tensorboard import SummaryWriter


def initialize_weights(modules, scale=1.0):
    for m in modules:
        if isinstance(m, nn.Conv2d):
            # Kaiming initializes weights with a normal distribution for faster convergence
            nn.init.kaiming_normal_(m.weight, a=0, mode='fan_in')
            m.weight.data *= scale
            if m.bias is not None:
                m.bias.data.zero_()

class ResidualBlock(nn.Module):
    # output = identity + out (for residue learning only)
    def __init__(self, nf=64):
        super().__init__()

        self.conv1 = nn.Conv2d(nf, nf, 3, 1, 1, bias=True)
        self.conv2 = nn.Conv2d(nf, nf, 3, 1, 1, bias=True)

        # initialization
        # small weight scale for small initial residue
        initialize_weights([self.conv1, self.conv2], 0.1)

    def forward(self, x):
        identity = x
        out = F.relu(self.conv1(x), inplace=True)
        out = self.conv2(out)
        return identity + out


class InvertibleBlock(nn.Module):
    def __init__(self, channels, clamp=1.0):
        super().__init__()

        self.channels = channels
        self.clamp = clamp

        # Three conv networks with the same architecture
        self.f = self._build_conv(channels)
        self.g = self._build_conv(channels)
        self.h = self._build_conv(channels)

    def _build_conv(self, channels):
        return nn.Sequential(
            nn.Conv2d(channels, channels, 3, padding=1),
            nn.LeakyReLU(0.2),

            ResidualBlock(channels),
            ResidualBlock(channels),

            nn.Conv2d(channels, channels, 3, padding=1),
        )

    def scale(self, s):
        # normalize exponent from (0, 1) to (-1, 1)
        return torch.exp(self.clamp * (torch.sigmoid(s) * 2 - 1))

    def forward(self, x_h, x_s):
        # Equation 1 — embedding direction
        x_h_next = x_h + self.f(x_s)
        x_s_next = self.scale(self.g(x_h_next)) * x_s + self.h(x_h_next)
        return x_h_next, x_s_next

    def inverse(self, x_h_next, x_s_next):
        # Equation 2 — extraction direction
        x_s = (x_s_next - self.h(x_h_next)) / self.scale(self.g(x_h_next))
        x_h = x_h_next - self.f(x_s)
        return x_h, x_s


class EnhanceModule(nn.Module):
    def __init__(self):
        super().__init__()

        self.conv1 = nn.Conv2d(3, 32, 3, padding=1)
        self.conv2 = nn.Conv2d(3 + 32, 32, 3, padding=1)
        self.conv3 = nn.Conv2d(3 + 2 * 32, 32, 3, padding=1)
        self.conv4 = nn.Conv2d(3 + 3 * 32, 32, 3, padding=1)

        # Final layer outputs back to 3 channels (RGB)
        self.conv5 = nn.Conv2d(3 + 4 * 32, 3, 3, padding=1)
        self.act = nn.LeakyReLU(0.2)

        initialize_weights([self.conv5], 0.)

    def forward(self, x):
        x1 = self.act(self.conv1(x))
        x2 = self.act(self.conv2(torch.cat([x, x1], 1)))
        x3 = self.act(self.conv3(torch.cat([x, x1, x2], 1)))
        x4 = self.act(self.conv4(torch.cat([x, x1, x2, x3], 1)))
        x5 = self.conv5(torch.cat([x, x1, x2, x3, x4], 1))

        return x5


class RoundWithGAF(torch.autograd.Function):
    @staticmethod
    def forward(ctx, x):
        return torch.round(x)  # real rounding in forward pass

    @staticmethod
    def backward(ctx, grad_output):
        # GAF gradient instead of zero gradient
        return grad_output  # passes gradient through unchanged

def round_gaf(x):
    return RoundWithGAF.apply(x)


class HaarDWT(nn.Module):
    def __init__(self):
        super().__init__()

        # fixed Haar filters as buffers
        ll = torch.tensor([[1, 1], [1, 1]], dtype=torch.float32) * 0.5      #(x01 + x02 + x03 + x04) * 0.5
        lh = torch.tensor([[1, -1], [1, -1]], dtype=torch.float32) * 0.5    #(x01 - x02 + x03 - x04) * 0.5
        hl = torch.tensor([[1, 1], [-1, -1]], dtype=torch.float32) * 0.5    #(x01 + x02 - x03 - x04) * 0.5
        hh = torch.tensor([[1, -1], [-1, 1]], dtype=torch.float32) * 0.5    #(x01 - x02 - x03 + x04) * 0.5

        # shape: [4, 1, 2, 2]
        kernel = torch.stack([ll, lh, hl, hh], dim=0).unsqueeze(1)
        self.register_buffer('kernel', kernel)

    def forward(self, x):
        B, C, H, W = x.shape

        # process each channel independently
        x = x.reshape(B * C, 1, H, W)

        out = F.conv2d(x, self.kernel, stride=2)  # [B*C, 4, H/2, W/2]
        out = out.reshape(B, C * 4, H // 2, W // 2)
        return out


class HaarIWT(nn.Module):
    def __init__(self):
        super().__init__()

        ll = torch.tensor([[1, 1], [1, 1]], dtype=torch.float32) * 0.5
        lh = torch.tensor([[1, -1], [1, -1]], dtype=torch.float32) * 0.5
        hl = torch.tensor([[1, 1], [-1, -1]], dtype=torch.float32) * 0.5
        hh = torch.tensor([[1, -1], [-1, 1]], dtype=torch.float32) * 0.5

        kernel = torch.stack([ll, lh, hl, hh], dim=0).unsqueeze(1)
        self.register_buffer('kernel', kernel)

    def forward(self, x):
        B, C4, H, W = x.shape
        C = C4 // 4

        x = x.reshape(B * C, 4, H, W)

        out = F.conv_transpose2d(x, self.kernel, stride=2)  # [B*C, 1, H*2, W*2]
        out = out.reshape(B, C, H * 2, W * 2)
        return out


class PRIS(nn.Module):
    def __init__(self, num_blocks=8):
        super().__init__()
        self.inv_blocks = nn.ModuleList([
            InvertibleBlock(channels=12)  # 12 because DWT does 4 channels from each RGB
            for _ in range(num_blocks)
        ])
        self.pre_enhance = EnhanceModule()
        self.post_enhance = EnhanceModule()

        self.dwt_layer = HaarDWT()
        self.iwt_layer = HaarIWT()

    def embed(self, host, secret):
        h, s = self.dwt(host), self.dwt(secret)
        for block in self.inv_blocks:
            h, s = block(h, s)
        container = self.iwt(h)

        container = container * 255.0
        container = round_gaf(container)
        container = container / 255.0
        return container

    def extract(self, container, use_enhance=False):
        if use_enhance:
            container = self.pre_enhance(container)
        c = self.dwt(container)
        z = torch.randn_like(c, device=c.device)  # Gaussian noise as placeholder
        for block in reversed(self.inv_blocks):
            c, z = block.inverse(c, z)
        secret = self.iwt(c)
        if use_enhance:
            secret = self.post_enhance(secret)
        return secret

    def dwt(self, x):
        return self.dwt_layer(x)

    def iwt(self, x):
        return self.iwt_layer(x)


# --------------------- ATTACKS ---------------------
def round_diff(x):
    sign = torch.ones_like(x)
    sign[torch.floor(x) % 2 == 0] = -1
    y = sign * torch.cos(x * torch.pi) / 2
    out = torch.round(x) + y - y.detach()
    return out

def apply_attack(container, attack_type=None):
    # distortions to simulate real-world attacks
    if attack_type is None:
        attack_type = random.choice(['gaussian', 'jpeg', 'round', 'none'])

    if attack_type == 'gaussian':
        level = random.choice([1, 10])
        noise = level * torch.randn_like(container) / 255.0
        return (container + noise).clamp(0, 1)

    elif attack_type == 'jpeg':
        level = random.choice([80, 90])
        jpeg = K.RandomJPEG(jpeg_quality=(level, level))
        return jpeg(container)

    elif attack_type == 'round':
        return round_diff(container * 255) / 255.0

    else:
        return container  # no attack


def compute_psnr(a, b):
    mse = F.mse_loss(a.clamp(0,1), b.clamp(0,1)).item()
    return 100.0 if mse == 0 else 10 * math.log10(1.0 / mse)


def _run_one_epoch(model, loader, device, step,
                   optimizer=None, use_enhance=False,
                   loss_c=True, loss_s=True, mode='train'):
    is_train = (mode == 'train')
    model.train() if is_train else model.eval()

    total_loss = 0.0
    total_psnr_c = 0.0
    total_psnr_s = 0.0
    n = 0

    context = torch.enable_grad() if is_train else torch.no_grad()
    with context:
        for host, secret, _, _ in loader:
            host = host.to(device, non_blocking=True)
            secret = secret.to(device, non_blocking=True)

            # embed
            container = model.embed(host, secret)

            if step == 1:
                attacked = apply_attack(container, 'none')
            else:
                attacked = apply_attack(container)  # random attack

            # extract
            extracted = model.extract(attacked, use_enhance)

            lc, ls = 0, 0
            # calc loss
            if loss_c:
                lc = F.mse_loss(container, host)
            if loss_s:
                ls = F.mse_loss(extracted, secret)
            loss = lc + ls

            if is_train:
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()

            with torch.no_grad():
                total_loss += loss.item()
                total_psnr_c += compute_psnr(container, host)
                total_psnr_s += compute_psnr(extracted, secret)
                n += 1

    return {
        'loss':   total_loss   / n,
        'psnr_c': total_psnr_c / n,
        'psnr_s': total_psnr_s / n,
    }

writer = None  # global writer
def _run_step(model, train_loader, val_loader, optimizer, scheduler,
              device, epochs, step, use_enhance, loss_c, loss_s,
              save_path, history, patience=50):
    global writer
    if writer is None:
        writer = SummaryWriter(comment='_PRIS')

    best_val_loss = float('inf')
    global_step_offset = sum(
        len(v['train_loss']) for v in
        [history]
    )

    for epoch in range(epochs):
        t0 = time.time()

        train_m = _run_one_epoch(
            model, train_loader, device, step, optimizer,
            use_enhance, loss_c, loss_s, 'train'
        )
        val_m = _run_one_epoch(
            model, val_loader, device, step, None,
            use_enhance, loss_c, loss_s, 'val'
        )

        scheduler.step()
        elapsed = time.time() - t0

        # record history
        history['train_loss'].append(round(train_m['loss'], 6))
        history['val_loss'].append(round(val_m['loss'], 6))
        history['psnr_c'].append(round(val_m['psnr_c'], 4))
        history['psnr_s'].append(round(val_m['psnr_s'], 4))

        # TensorBoard
        idx = len(history['train_loss']) - 1
        writer.add_scalars(f'step{step}/Loss',
            {'train': train_m['loss'], 'val': val_m['loss']}, idx)
        writer.add_scalars(f'step{step}/PSNR_C',
            {'train': train_m['psnr_c'], 'val': val_m['psnr_c']}, idx)
        writer.add_scalars(f'step{step}/PSNR_S',
            {'train': train_m['psnr_s'], 'val': val_m['psnr_s']}, idx)
        writer.add_scalar(f'step{step}/LR',
            optimizer.param_groups[0]['lr'], idx)

        # console
        if epoch % 10 == 0:
            print(
                f"\t[{epoch:4d}/{epochs}] "
                f"loss={train_m['loss']:.5f} val={val_m['loss']:.5f} | "
                f"PSNR-C={val_m['psnr_c']:.2f} PSNR-S={val_m['psnr_s']:.2f} | "
                f"lr={optimizer.param_groups[0]['lr']:.2e} | "
                f"{elapsed:.1f}s"
            )

        # save best checkpoint
        if val_m['loss'] < best_val_loss:
            best_val_loss = val_m['loss']
            torch.save(model.state_dict(), save_path)

        '''
        # early stopping — if val loss hasn't improved in 50 epochs, stop
        if len(history['val_loss']) > patience:
            recent = history['val_loss'][-patience:]
            if min(recent) >= history['val_loss'][-(patience+1)]:
                print(f"\tEarly stopping at epoch {epoch} (no improvement in {patience} epochs)")
                break
        '''

    writer.flush()


def train(model, train_loader, val_loader, device="cpu", epochs=10):
    history = {
        'step1': {'train_loss': [], 'val_loss': [], 'psnr_c': [], 'psnr_s': []},
        'step2': {'train_loss': [], 'val_loss': [], 'psnr_c': [], 'psnr_s': []},
        'step3': {'train_loss': [], 'val_loss': [], 'psnr_c': [], 'psnr_s': []},
    }


    # -----------------------------------------
    # Step 1 — train only the invertible blocks
    # -----------------------------------------
    print ('\n\n=== Step 1: Training invertible blocks ===')

    for param in model.inv_blocks.parameters():
        param.requires_grad = True
    for param in model.pre_enhance.parameters():
        param.requires_grad = False
    for param in model.post_enhance.parameters():
        param.requires_grad = False

    optimizer = torch.optim.Adam(
        filter(lambda p: p.requires_grad, model.parameters()),
        lr=1e-4, betas=(0.9, 0.99), eps=1e-6)

    # cosine LR loss smoothly
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
        optimizer, T_max=epochs, eta_min=1e-6
    )

    _run_step(model, train_loader, val_loader, optimizer, scheduler,
              device, epochs, 1, False, True, True,
              'model_step1.pth', history['step1'])
    torch.save(model.state_dict(), 'model_step1.pth')
    print('Step 1 done, saved model_step1.pth')


    # -----------------------------------------
    # Step 2 — train only the enhance modules
    # -----------------------------------------
    print ('\n\n=== Step 2: Training enhance modules ===')

    for param in model.inv_blocks.parameters():
        param.requires_grad = False
    for param in model.pre_enhance.parameters():
        param.requires_grad = True
    for param in model.post_enhance.parameters():
        param.requires_grad = True

    optimizer = torch.optim.Adam(
        filter(lambda p: p.requires_grad, model.parameters()),
        lr=1e-4, betas=(0.9, 0.99), eps=1e-6)

    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
        optimizer, T_max=epochs, eta_min=1e-6
    )

    _run_step(model, train_loader, val_loader, optimizer, scheduler,
              device, epochs, 2, True, False, True,
              'model_step2.pth', history['step2'], 300)
    torch.save(model.state_dict(), 'model_step2.pth')
    print('Step 2 done, saved model_step2.pth')


    # -----------------------------------------
    # Step 3 — finetuning
    # -----------------------------------------
    print ('\n\n=== Step 3: Finetuning ===')

    for param in model.parameters():
        param.requires_grad = True

    optimizer = torch.optim.Adam([
        {'params': model.inv_blocks.parameters(), 'lr': 1e-6},  # very low
        {'params': model.pre_enhance.parameters(), 'lr': 1e-5},
        {'params': model.post_enhance.parameters(), 'lr': 1e-5},
    ], betas=(0.9, 0.99), eps=1e-6)

    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
        optimizer, T_max=epochs, eta_min=1e-7
    )

    _run_step(model, train_loader, val_loader, optimizer, scheduler,
              device, epochs, 3,True, True, True,
              'model_step3.pth', history['step3'], 300)

    torch.save(model.state_dict(), 'model_step3.pth')
    print('Step 3 done, saved model_step3.pth')

    _save_history(history)
    print('\nTraining complete.')
    return history


def _save_history(history):
    with open('training_history.json', 'w') as f:
        json.dump(history, f, indent=2)
    print("History saved to training_history.json")
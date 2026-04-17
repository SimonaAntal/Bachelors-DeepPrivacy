import random

import torch
import torch.nn as nn
import torch.nn.functional as F
import io
from PIL import Image
import torchvision.transforms.functional as TF

class InvertibleBlock(nn.Module):
    def __init__(self, channels):
        super().__init__()

        # Three conv networks with the same architecture
        self.f = self._build_conv(channels)
        self.g = self._build_conv(channels)
        self.h = self._build_conv(channels)

    def _build_conv(self, channels):
        return nn.Sequential(
            nn.Conv2d(channels, channels, 3, padding=1),
            nn.LeakyReLU(0.2),
            nn.Conv2d(channels, channels, 3, padding=1),
        )

    def forward(self, x_h, x_s):
        # Equation 1 — embedding direction
        x_h_next = x_h + self.f(x_s)
        x_s_next = x_s * torch.exp(torch.sigmoid(self.g(x_h_next))) + self.h(x_h_next)
        return x_h_next, x_s_next

    def inverse(self, x_h_next, x_s_next):
        # Equation 2 — extraction direction
        x_s = (x_s_next - self.h(x_h_next)) * torch.exp(-torch.sigmoid(self.g(x_h_next)))
        x_h = x_h_next - self.f(x_s)
        return x_h, x_s


class EnhanceModule(nn.Module):
    def __init__(self):
        super().__init__()

        # layer list
        self.layers = nn.ModuleList()
        in_channels = 3     # 3 channels RGB

        # 4 layers with 32 channels
        for i in range(4):
            self.layers.append(nn.Sequential(
                nn.Conv2d(in_channels + i * 32, 32, 3, padding=1),
                nn.LeakyReLU(0.2)
            ))

        # Final layer outputs back to 3 channels (RGB)
        self.final = nn.Conv2d(in_channels + 4 * 32, 3, 3, padding=1)

    def forward(self, x):
        features = [x]

        for layer in self.layers:
            out = layer(torch.cat(features, dim=1))
            features.append(out)

        return self.final(torch.cat(features, dim=1))


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
        super(HaarDWT, self).__init__()

    def forward(self, x):
        # x: [B, C, H, W]

        # split the image in 4 sub-matrix
        x01 = x[:, :, 0::2, 0::2]  # lin even, col even
        x02 = x[:, :, 1::2, 0::2]  # lin odd, col even
        x03 = x[:, :, 0::2, 1::2]  # lin even, col odd
        x04 = x[:, :, 1::2, 1::2]  # lin odd, col odd

        # Haar coeffs
        yl = (x01 + x02 + x03 + x04) / 2.0  # LL
        yh_h = (x01 - x02 + x03 - x04) / 2.0  # LH
        yh_v = (x01 + x02 - x03 - x04) / 2.0  # HL
        yh_d = (x01 - x02 - x03 + x04) / 2.0  # HH

        # combine in a tensor [B, C, 3, H/2, W/2]
        yh = torch.stack([yh_h, yh_v, yh_d], dim=2)

        return yl, [yh]


class HaarIWT(nn.Module):
    def __init__(self):
        super(HaarIWT, self).__init__()

    def forward(self, input):
        yl, yh_list = input
        yh = yh_list[0]

        yh_h = yh[:, :, 0, :, :]
        yh_v = yh[:, :, 1, :, :]
        yh_d = yh[:, :, 2, :, :]

        # pixel reconstruction
        x01 = (yl + yh_h + yh_v + yh_d) / 2.0
        x02 = (yl - yh_h + yh_v - yh_d) / 2.0
        x03 = (yl + yh_h - yh_v - yh_d) / 2.0
        x04 = (yl - yh_h - yh_v + yh_d) / 2.0

        # pixel alignment
        B, C, H, W = yl.shape
        reconstructed = torch.zeros((B, C, H * 2, W * 2), device=yl.device, dtype=yl.dtype)
        reconstructed[:, :, 0::2, 0::2] = x01
        reconstructed[:, :, 1::2, 0::2] = x02
        reconstructed[:, :, 0::2, 1::2] = x03
        reconstructed[:, :, 1::2, 1::2] = x04

        return reconstructed


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
        container = round_gaf(container * 255) / 255  # rounding
        return container

    def extract(self, container, use_enhance=False):
        if use_enhance:
            container = self.pre_enhance(container)
        c = self.dwt(container)
        z = torch.randn_like(c)  # Gaussian noise as placeholder
        for block in reversed(self.inv_blocks):
            c, z = block.inverse(c, z)
        secret = self.iwt(c)
        if use_enhance:
            secret = self.post_enhance(secret)
        return secret

    def dwt(self, x):
        yl, yh = self.dwt_layer(x)
        # yl: (B, C, H/2, W/2) LL
        # yh: (B, C, 3, H/2, W/2)
        # dims: LH, HL, HH

        yh = yh[0]
        B, C, _, H, W = yh.shape
        yh = yh.view(B, C * 3, H, W)

        return torch.cat([yl, yh], dim=1)  # 3C → 12C

    def iwt(self, x):
        B, C, H, W = x.shape
        yl = x[:, :C // 4, :, :] # first channels (LL)
        yh = x[:, C // 4:, :, :] # the rest (LH + HL + HH)

        yh = yh.view(B, C // 4, 3, H, W)
        yh = [yh]

        return self.iwt_layer((yl, yh))



def apply_attack(container, attack_type=None):
    # random distortion to simulate real-world attacks

    if attack_type is None:
        attack_type = random.choice(['gaussian', 'jpeg', 'round', 'none'])

    if attack_type == 'gaussian':
        sigma = random.choice([1, 10]) / 255.0
        noise = torch.randn_like(container) * sigma
        return (container + noise).clamp(0, 1)

    elif attack_type == 'jpeg':
        quality = random.choice([80, 90])
        result = []

        for img in container:
            pil = TF.to_pil_image(img.cpu().clamp(0, 1))
            buf = io.BytesIO()
            pil.save(buf, format='JPEG', quality=quality)
            buf.seek(0)
            pil_comprim = Image.open(buf)
            result.append(TF.to_tensor(pil_comprim))
        return torch.stack(result).to(container.device)

    elif attack_type == 'round':
        return (container * 255).round() / 255.0

    else:
        return container  # no attack


def run_epochs(model, dataloader, optimizer, device,
               epochs, step, lr_step, loss_c=True, loss_s=True, use_enhance=False):
    for epoch in range(epochs):
        epoch_loss = 0.0

        for host, secret, _, _ in dataloader:
            host = host.to(device)
            secret = secret.to(device)

            # embed
            container = model.embed(host, secret)

            if step == 1:
                attacked = apply_attack(container, 'none')
            else:
                attacked = apply_attack(container)  # random attack

            # extract
            extracted = model.extract(attacked, use_enhance)

            # loss
            loss_container, loss_secret = 0.0, 0.0

            if loss_c:
                loss_container = F.mse_loss(container, host)
            if loss_s:
                loss_secret = F.mse_loss(extracted, secret)

            loss = loss_container + loss_secret

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            epoch_loss += loss.item()

        # modify learning rate every 200 epochs
        if epoch % 200 == 0 and epoch != 0:
            for g in optimizer.param_groups:
                g['lr'] *= lr_step

        if epoch % 10 == 0:
            avg_loss = epoch_loss / len(dataloader)
            print(f'Epoch {epoch}/{epochs}, Avg Loss: {avg_loss}')


def train(model, dataloader, device="cpu", epochs=10):
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
        filter(lambda p: p.requires_grad, model.parameters()), # only training params
        lr=1e-4)

    run_epochs(model, dataloader, optimizer, device, epochs, 1,
               0.5, True, True, False)
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
        filter(lambda p: p.requires_grad, model.parameters()), # only training params
        lr=1e-4)

    run_epochs(model, dataloader, optimizer, device, epochs, 2,
               0.5, False, True, True)
    torch.save(model.state_dict(), 'model_step2.pth')
    print('Step 2 done, saved model_step2.pth')


    # -----------------------------------------
    # Step 3 — finetuning
    # -----------------------------------------
    print ('\n\n=== Step 3: Finetuning ===')

    for param in model.parameters():
        param.requires_grad = True

    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=1e-5)

    run_epochs(model, dataloader, optimizer, device, epochs, 3,
               0.5, True, True, True)
    torch.save(model.state_dict(), 'model_step3.pth')
    print('Step 3 done, saved model_step3.pth')
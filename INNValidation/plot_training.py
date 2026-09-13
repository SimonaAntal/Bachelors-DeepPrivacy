import json
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np
import sys

# ---- load history ----
path = sys.argv[1] if len(sys.argv) > 1 else "training_history.json"
with open(path) as f:
    history = json.load(f)

steps = ['step1', 'step2', 'step3']
colors = {'step1': '#4C72B0', 'step2': '#DD8452', 'step3': '#55A868'}
labels = {'step1': 'Etapa 1 (INN)', 'step2': 'Etapa 2 (Enhance)', 'step3': 'Etapa 3 (Finetuning)'}

fig, axes = plt.subplots(2, 2, figsize=(14, 8))
fig.suptitle('Evoluția antrenării modelului PRIS', fontsize=14, fontweight='bold')

# offset pentru x ca sa apara continuu
offset = 0
step_boundaries = []

for step in steps:
    h = history[step]
    n = len(h['train_loss'])
    x = np.arange(offset, offset + n)

    # Train/Val Loss
    axes[0, 0].plot(x, h['train_loss'], color=colors[step], label=f"{labels[step]} - Train", linewidth=1.2)
    axes[0, 0].plot(x, h['val_loss'], color=colors[step], linestyle='--', label=f"{labels[step]} - Val", linewidth=1.2, alpha=0.7)

    # PSNR-C
    axes[0, 1].plot(x, h['psnr_c'], color=colors[step], label=labels[step], linewidth=1.2)

    # PSNR-S
    axes[1, 0].plot(x, h['psnr_s'], color=colors[step], label=labels[step], linewidth=1.2)

    # Val Loss doar
    axes[1, 1].plot(x, h['val_loss'], color=colors[step], label=labels[step], linewidth=1.2)

    step_boundaries.append(offset)
    offset += n

# linii verticale la granita dintre etape
for ax in axes.flat:
    for b in step_boundaries[1:]:
        ax.axvline(x=b, color='gray', linestyle=':', alpha=0.5, linewidth=1)

axes[0, 0].set_title('Train Loss vs Validation Loss')
axes[0, 0].set_xlabel('Epocă')
axes[0, 0].set_ylabel('Loss (MSE)')
axes[0, 0].legend(fontsize=7)
axes[0, 0].grid(True, alpha=0.3)

axes[0, 1].set_title('PSNR-C (Container vs Host)')
axes[0, 1].set_xlabel('Epocă')
axes[0, 1].set_ylabel('PSNR (dB)')
axes[0, 1].legend(fontsize=8)
axes[0, 1].grid(True, alpha=0.3)

axes[1, 0].set_title('PSNR-S (Secret vs Recovered)')
axes[1, 0].set_xlabel('Epocă')
axes[1, 0].set_ylabel('PSNR (dB)')
axes[1, 0].legend(fontsize=8)
axes[1, 0].grid(True, alpha=0.3)

axes[1, 1].set_title('Validation Loss per etapă')
axes[1, 1].set_xlabel('Epocă')
axes[1, 1].set_ylabel('Loss (MSE)')
axes[1, 1].legend(fontsize=8)
axes[1, 1].grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('training_history.png', dpi=150, bbox_inches='tight')
print("Salvat: training_history.png")

# ---- print summary ----
print("\n=== Sumar antrenare ===")
for step in steps:
    h = history[step]
    n = len(h['train_loss'])
    print(f"\n{labels[step]}: {n} epoci")
    print(f"  Loss final train: {h['train_loss'][-1]:.6f}")
    print(f"  Loss final val:   {h['val_loss'][-1]:.6f}")
    print(f"  PSNR-C final:     {h['psnr_c'][-1]:.2f} dB")
    print(f"  PSNR-S final:     {h['psnr_s'][-1]:.2f} dB")

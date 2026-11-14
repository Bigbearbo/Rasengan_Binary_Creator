"""Public audit copy of R19's only architecture change.

Same 10,457-parameter feed-forward network as R18; first answer word sees a,
cursor positions 6..11 see b only. **POST-RUN ERRATUM:** for r1, STOP is
already at cursor6 and therefore ALSO sees only b; this violated the frozen
prose intent to leave STOP unchanged. r2 STOP at cursor12 still sees all. Actual frozen training runner
SHA256 2705913fe770783778cb45bed586eecfa397fccb86433cc0c9d392720c3da682
and exact checkpoints live in the R19 companion ZIP. This isolated file is
not a replacement for the complete frozen runner.
"""
import torch
from torch import nn
from torch.nn import functional as F

EMB = 16
H = 94
INPUT_LENGTH = 80
Q_LENGTH = 39
PARAMETERS = 10457
DENSE_FORWARD_MAC = 10920


class DualRoutedStudent(nn.Module):
    def __init__(self):
        super().__init__()
        self.enc = nn.Linear(12, EMB)
        self.hidden = nn.Linear(4 * EMB + 8 + 33, H)
        self.out = nn.Linear(H, 3)

    def forward(self, x):
        z = x.reshape(-1, INPUT_LENGTH, 2)
        q = z[:, 9:33, :].reshape(-1, 4, 12)
        cursor = z.sum(-1).sum(-1).long() - Q_LENGTH
        first = (cursor < 6).reshape(-1, 1, 1)
        second = ((cursor >= 6) & (cursor < 12)).reshape(-1, 1, 1)
        only_a = torch.tensor([1., 0., 0., 0.], dtype=q.dtype, device=q.device).reshape(1, 4, 1)
        only_b = torch.tensor([0., 1., 0., 0.], dtype=q.dtype, device=q.device).reshape(1, 4, 1)
        q = torch.where(first, q * only_a, torch.where(second, q * only_b, q))
        e = torch.tanh(self.enc(q))
        pos = F.one_hot(cursor.clamp(0, 32), num_classes=33).to(x.dtype)
        feat = torch.cat([e.reshape(-1, 64), z[:, 5:9, :].reshape(-1, 8), pos], dim=-1)
        return self.out(torch.tanh(self.hidden(feat)))


if __name__ == "__main__":
    net = DualRoutedStudent()
    assert sum(t.numel() for t in net.parameters()) == PARAMETERS
    assert 4 * 12 * EMB + (4 * EMB + 8 + 33) * H + H * 3 == DENSE_FORWARD_MAC
    print("R19 architecture static count PASS")

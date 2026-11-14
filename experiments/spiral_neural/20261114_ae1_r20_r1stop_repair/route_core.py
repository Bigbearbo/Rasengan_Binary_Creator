"""R20 PUBLIC architecture audit twin (not complete frozen trainer).

Parent R19 source PR #68, original public audit route_core.py.
Only neural semantic change: r2-only second mask; r1 STOP sees all word inputs.
Frozen complete runner SHA256 dbfad19c66ae2dd3f20113e8eb7e965fd576f9984462fd6a82c029897a28f15e
Pretraining Git commit 4878a53c4628f298da73f66320197a70f28304f5.
Full 3-seed checkpoint, exact training, and independent NumPy verification are in R20 companion ZIP.
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
        second = ((cursor >= 6) & (cursor < 12) & (z[:, 6, 1] > 0.5)).reshape(-1, 1, 1)
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
    print("R20 architecture static count PASS")

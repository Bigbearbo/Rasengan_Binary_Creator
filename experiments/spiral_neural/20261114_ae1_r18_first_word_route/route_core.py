"""Public R18 route-only model core; exact frozen runner remains in companion ZIP.
Run: python route_core.py /path/to/r14_source (PyTorch and NumPy required).
This is a static structural audit, NOT evidence of student learning.
"""
from pathlib import Path
import importlib.util,sys
import torch
from torch import nn
from torch.nn import functional as F

class FirstWordRoutedStudent(nn.Module):
 def __init__(self,src):
  super().__init__()
  self.enc=nn.Linear(12,src.EMB)
  self.hidden=nn.Linear(4*src.EMB+8+33,src.H)
  self.out=nn.Linear(src.H,3)
 def forward(self,x):
  z=x.reshape(-1,80,2)
  q=z[:,9:33,:].reshape(-1,4,12)
  cursor=z.sum(-1).sum(-1).long()-39
  is_first=(cursor<6).reshape(-1,1,1)
  mask=torch.tensor([1,0,0,0],dtype=q.dtype,device=q.device).reshape(1,4,1)
  masked=torch.where(is_first,q*mask,q)
  e=torch.tanh(self.enc(masked))
  pos=F.one_hot(cursor.clamp(0,32),num_classes=33).to(x.dtype)
  feat=torch.cat([e.reshape(-1,64),z[:,5:9,:].reshape(-1,8),pos],dim=-1)
  return self.out(torch.tanh(self.hidden(feat)))

if __name__=='__main__':
 src=Path(sys.argv[1])
 spec=importlib.util.spec_from_file_location('r14',src/'run.py')
 m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 student=FirstWordRoutedStudent(m)
 assert sum(p.numel() for p in student.parameters())==10457
 with torch.no_grad():
  for i in range(6):
   a=m.word(25)[:i]
   x=torch.from_numpy(m.xvec(m.question(2,25,16,0,2)+a)).unsqueeze(0)
   y=torch.from_numpy(m.xvec(m.question(2,25,20,0,2)+a)).unsqueeze(0)
   assert torch.equal(student(x),student(y)),i
 print('ROUTE STATIC AUDIT PASS: 10457 params; first 6 positions invariant to b16/20')

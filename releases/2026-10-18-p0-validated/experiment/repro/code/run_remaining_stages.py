"""Continue the approved fixed experiment, only after current initial stage closes."""
import subprocess
import sys
import time
from effect_common import *

p=OUT/'api/development_initial/completion.json';deadline=time.monotonic()+7200
while not p.exists():
    if time.monotonic()>deadline:raise TimeoutError('development initial not complete')
    time.sleep(2)
if not read(p)['complete']:raise ValueError('initial stage incomplete')
for split in ('development','holdout'):
    if split=='holdout':subprocess.run([sys.executable,'-S','-X','utf8','-B',str(WORK/'api_runner.py'),'holdout_initial'],check=True)
    subprocess.run([sys.executable,'-S','-X','utf8','-B',str(WORK/'prepare_judgments.py'),split],check=True)
    subprocess.run([sys.executable,'-S','-X','utf8','-B',str(WORK/'api_runner.py'),split+'_judgment'],check=True)
print('All fixed inference phases terminal; no scoring references opened.',flush=True)

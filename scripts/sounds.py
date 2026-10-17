"""Original synthesized effects, no third-party audio samples."""
import math
from pathlib import Path
import struct
import wave
dest=Path(__file__).resolve().parents[1]/'assets/shared/audio'
dest.mkdir(parents=True,exist_ok=True)
for name,duration in [('pop',.22),('tick',.1),('sparkle',.75)]:
    samples=[]
    for i in range(round(duration*48000)):
        t=i/48000
        envelope=min(1,t/.008)*max(0,1-t/duration)**2
        if name=='pop': value=math.sin(math.tau*(600*t-850*t*t))
        elif name=='tick': value=math.sin(math.tau*1000*t)
        else: value=sum(math.sin(math.tau*f*t) for f in (1046.5,1318.5,1568))/3
        samples.append(struct.pack('<h',round(16000*envelope*value)))
    with wave.open(str(dest/f'{name}.wav'),'wb') as out:
        out.setparams((1,2,48000,0,'NONE','not compressed'))
        out.writeframes(b''.join(samples))
print('Created pop, tick, sparkle')

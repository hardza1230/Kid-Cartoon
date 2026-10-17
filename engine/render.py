"""Repository-relative episode compositor. Requires Pillow with RAQM and FFmpeg."""
import argparse
import json
import math
from pathlib import Path
import subprocess
from PIL import Image, ImageDraw, ImageFont, ImageOps, features

ROOT=Path(__file__).resolve().parents[1]
FONT=ROOT/'assets/shared/fonts/NotoSansThai.ttf'

def load(episode):
    d=json.loads((ROOT/'episodes'/episode/'episode.json').read_text())
    assert d['id']==episode and d['width']%2==d['height']%2==0
    assert features.check('raqm'), 'Pillow needs RAQM to shape Thai text correctly'
    cursor=0
    for s in d['scenes']:
        assert s['start']==cursor and s['end']>cursor
        assert all(0<=i<d['sprite']['columns']*d['sprite']['rows'] for i in s['frames'])
        cursor=s['end']
    assert cursor==d['duration']
    return d

def cells(path,cols,rows):
    sheet=Image.open(path).convert('RGBA')
    return [sheet.crop((round(c*sheet.width/cols),round(r*sheet.height/rows),round((c+1)*sheet.width/cols),round((r+1)*sheet.height/rows))) for r in range(rows) for c in range(cols)]

class Compositor:
    def __init__(self,d):
        self.d=d
        self.size=(d['width'],d['height'])
        self.bg=ImageOps.fit(Image.open(ROOT/d['background']).convert('RGB'),self.size)
        self.sprites=cells(ROOT/d['sprite']['path'],d['sprite']['columns'],d['sprite']['rows'])
        self.decor=cells(ROOT/d['decorations'],2,2)
        self.fonts={}

    def frame(self,t):
        d=self.d; w,h=self.size
        t=max(0,min(t,d['duration']-1/d['fps']))
        s=next(s for s in d['scenes'] if s['start']<=t<s['end'])
        local=t-s['start']
        out=self.bg.copy().convert('RGBA')
        draw=ImageDraw.Draw(out)
        def text(value,y,size,color):
            while True:
                if size not in self.fonts: self.fonts[size]=ImageFont.truetype(str(FONT),size)
                font=self.fonts[size]
                if draw.textlength(value,font=font)<=w*.8: break
                size-=1
            draw.text((w/2,y),value,font=font,anchor='mm',fill=color)
        draw.rounded_rectangle((w*.07,h*.09,w*.93,h*.34),radius=36,fill='#fffbec')
        text('KID CARTOON • ENGLISH + ไทย',h*.13,20,'#9a6952')
        title=str(max(1,3-int(local*3))) if s['effect']=='countdown' else s['title']
        text(title,h*.215,68,'#72422b')
        text(s['subtitle'],h*.29,30,'#bd6046')
        idx=s['frames'][int(local*s['rate'])%len(s['frames'])]
        scale=1+.025*math.sin(t*math.tau)
        if s['effect']=='bounce': scale*=.85+.15*min(1,local*3)
        if s['effect']=='reveal': scale*=1+.10*math.exp(-local*4)
        side=round(w*.74*scale)
        sprite=self.sprites[idx].resize((side,side),Image.Resampling.LANCZOS)
        out.alpha_composite(sprite,(round((w-side)/2),round(h*.79+7*math.sin(t*math.tau)-side)))
        if t>=5:
            for j,x,y in [(0,.12,.45),(1,.76,.44),(3,.78,.67)]:
                z=round(w*(.12+.015*math.sin(t*4+j)))
                out.alpha_composite(self.decor[j].resize((z,z),Image.Resampling.LANCZOS),(round(w*x),round(h*y)))
        draw=ImageDraw.Draw(out)
        draw.rounded_rectangle((w*.13,h*.83,w*.87,h*.89),radius=22,fill='#fff8e6')
        text('ฟัง • ทาย • พูดตาม',h*.86,26,'#805035')
        draw.rounded_rectangle((w*.12,h*.92,w*.88,h*.925),radius=3,fill='#fff8e6')
        draw.rounded_rectangle((w*.12,h*.92,w*(.12+.76*t/d['duration']),h*.925),radius=3,fill='#e98d64')
        return out.convert('RGB')

def duration(path):
    return float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',str(path)]))

def audio_mix(d,episode,dest):
    clips=[]
    for i,item in enumerate(d['narration']):
        path=ROOT/'episodes'/episode/'audio'/item['file']
        end=item['start']+duration(path)
        limit=d['narration'][i+1]['start'] if i+1<len(d['narration']) else d['duration']
        if end>limit: raise ValueError(f'{path.name} ends at {end:.2f}s, after next cue {limit}s')
        clips.append((path,item['start'],1))
    clips.extend((ROOT/'assets/shared/audio'/s['file'],s['start'],s['gain']) for s in d['sounds'])
    cmd=['ffmpeg','-y','-v','error','-f','lavfi','-i',f'anullsrc=r=48000:cl=stereo:d={d["duration"]}']
    for path,_,_ in clips: cmd+=['-i',str(path)]
    filters=[f'[{i}:a]aresample=48000,volume={gain},adelay={round(start*1000)}:all=1[a{i}]' for i,(_,start,gain) in enumerate(clips,1)]
    filters.append('[0:a]'+''.join(f'[a{i}]' for i in range(1,len(clips)+1))+f'amix=inputs={len(clips)+1}:duration=first:normalize=0,alimiter=limit=0.95:latency=1[mix]')
    subprocess.run(cmd+['-filter_complex',';'.join(filters),'-map','[mix]','-t',str(d['duration']),str(dest)],check=True)

def srt(d,path):
    def stamp(t):
        m=round(t*1000)
        return f'{m//3600000:02}:{m//60000%60:02}:{m//1000%60:02},{m%1000:03}'
    path.write_text('\n\n'.join(f'{i}\n{stamp(s["start"])} --> {stamp(s["end"])}\n{s["title"]}\n{s["subtitle"]}' for i,s in enumerate(d['scenes'],1))+'\n',encoding='utf-8')

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--episode',default='001-cat',choices=[x.name for x in (ROOT/'episodes').iterdir() if x.is_dir()])
    p.add_argument('--out',default='build')
    args=p.parse_args(); d=load(args.episode); c=Compositor(d)
    dest=Path(args.out); dest.mkdir(parents=True,exist_ok=True)
    audio_mix(d,args.episode,dest/'mix.wav')
    srt(d,dest/f'{args.episode}.srt')
    board=Image.new('RGB',(720,960),'#fff8e6')
    for i,s in enumerate(d['scenes']):
        board.paste(c.frame(s['start']+.5).resize((180,320)),((i%3)*240+30,(i//3)*480+40))
        ImageDraw.Draw(board).text(((i%3)*240+30,(i//3)*480+375),f'{s["start"]}–{s["end"]} sec',font=ImageFont.truetype(str(FONT),24),fill='#72422b')
    board.save(dest/'storyboard.png'); c.frame(7.5).save(dest/'poster.png')
    cmd=['ffmpeg','-y','-v','error','-f','rawvideo','-pix_fmt','rgb24','-s',f'{d["width"]}x{d["height"]}','-r',str(d['fps']),'-i','pipe:0','-i',str(dest/'mix.wav'),'-map','0:v:0','-map','1:a:0','-c:v','libx264','-preset','fast','-crf','19','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-t',str(d['duration']),'-movflags','+faststart',str(dest/f'{args.episode}.mp4')]
    proc=subprocess.Popen(cmd,stdin=subprocess.PIPE)
    try:
        for i in range(round(d['fps']*d['duration'])): proc.stdin.write(c.frame(i/d['fps']).tobytes())
    finally: proc.stdin.close()
    if proc.wait(): raise RuntimeError('FFmpeg failed')
    print(f'Rendered {dest/args.episode}.mp4')

if __name__=='__main__': main()

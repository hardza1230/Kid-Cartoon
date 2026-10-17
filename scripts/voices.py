"""Generate neural speech once; trim padding, preserve existing finished files."""
import argparse
import asyncio
import json
from pathlib import Path
import subprocess
import edge_tts
import edge_tts.communicate

ROOT=Path(__file__).resolve().parents[1]
# Add system CA roots while retaining verification and certifi's public roots.
edge_tts.communicate._SSL_CTX.load_default_certs()

async def main():
    p=argparse.ArgumentParser()
    p.add_argument('--episode',default='001-cat')
    args=p.parse_args()
    folder=ROOT/'episodes'/args.episode
    data=json.loads((folder/'episode.json').read_text())
    (folder/'audio').mkdir(exist_ok=True)
    for clip in data['narration']:
        target=folder/'audio'/clip['file']
        if target.exists() and target.stat().st_size:
            continue
        temp=target.with_suffix('.part.mp3')
        trim='silenceremove=start_periods=1:start_duration=0.02:start_threshold=-45dB:start_silence=0.06'
        for attempt in range(3):
            try:
                await asyncio.wait_for(edge_tts.Communicate(clip['text'],clip['voice'],rate='+5%').save(str(temp)),45)
                if not temp.stat().st_size:
                    raise RuntimeError('Empty speech response')
                subprocess.run(['ffmpeg','-y','-v','error','-i',str(temp),'-af',trim+',areverse,'+trim+',areverse','-c:a','libmp3lame','-q:a','2',str(target)],check=True)
                print(target.relative_to(ROOT),flush=True)
                break
            except Exception:
                target.unlink(missing_ok=True)
                if attempt==2:
                    raise
            finally:
                temp.unlink(missing_ok=True)

if __name__=='__main__':
    asyncio.run(main())

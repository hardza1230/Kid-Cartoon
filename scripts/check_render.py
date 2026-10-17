import json
import subprocess
import sys
from pathlib import Path
d=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',sys.argv[1]]))
v=next(s for s in d['streams'] if s['codec_type']=='video')
a=next(s for s in d['streams'] if s['codec_type']=='audio')
episode=json.loads(Path(sys.argv[2] if len(sys.argv)>2 else 'episodes/001-cat/episode.json').read_text())
assert (v['width'],v['height'])==(episode['width'],episode['height'])
assert v['r_frame_rate']==f'{episode["fps"]}/1'
assert v['codec_name']=='h264' and a['codec_name']=='aac'
assert abs(float(d['format']['duration'])-episode['duration'])<.1
assert int(v['nb_frames'])==episode['fps']*episode['duration']
print(f'Verified: {v["width"]}x{v["height"]}, {v["nb_frames"]} frames, H.264 + AAC')

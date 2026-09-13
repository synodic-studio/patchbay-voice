#!/usr/bin/env python3
"""Calibrate recording startup delay against screenshot anchors. Review scores."""
import argparse,json,statistics,subprocess
from pathlib import Path
from PIL import Image, ImageChops, ImageStat

p=argparse.ArgumentParser(description=__doc__);p.add_argument('run',type=Path);a=p.parse_args();r=a.run
m=json.loads((r/'manifest.json').read_text());start=m['recording_started_at']
names=['turn-0-input','turn-1-input','turn-0-answer','turn-1-answer']
targets={n:Image.open(r/f'{n}.png').convert('L').resize((160,348)) for n in names}
best={n:(999,None) for n in names}
proc=subprocess.Popen(['ffmpeg','-v','error','-i',str(r/'simulator.mp4'),'-vf','fps=5,scale=160:348','-pix_fmt','gray','-f','rawvideo','-'],stdout=subprocess.PIPE)
i=0
while True:
 data=proc.stdout.read(160*348)
 if not data:break
 if len(data)!=160*348:raise RuntimeError('Incomplete frame')
 frame=Image.frombytes('L',(160,348),data)
 for name,target in targets.items():
  score=ImageStat.Stat(ImageChops.difference(frame,target).crop((0,30,160,330))).mean[0]
  if score<best[name][0]:best[name]=(score,i/5)
 i+=1
assert proc.wait()==0
result={n:{'difference':score,'video_seconds':t,'wall_offset':float((r/f'{n}.png.timestamp').read_text())-start-t} for n,(score,t) in best.items()}
(r/'alignment.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))

inputs=[result[n] for n in ['turn-0-input','turn-1-input']]
if any(item['difference'] > 8 for item in inputs):
    raise SystemExit('Screenshot match is weak; inspect alignment.json before rendering')
if abs(inputs[0]['wall_offset'] - inputs[1]['wall_offset']) > 1:
    raise SystemExit('Input anchors disagree; inspect alignment before rendering')
m['recording_startup_offset_seconds']=statistics.mean(item['wall_offset'] for item in inputs)
m['alignment_method']='Two input screenshot anchors, 5fps image matching; approximate editorial synchronization'
(r/'manifest.json').write_text(json.dumps(m,indent=2))

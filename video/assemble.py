"""Two-stage assembly. Stage 1: each clip -> 1080x1350 30fps segment (parallel). Stage 2: xfade + overlay + subs + voice."""
import subprocess, sys, os
from concurrent.futures import ThreadPoolExecutor
from PIL import Image, ImageDraw, ImageFilter
CLIPDIR = sys.argv[1] if len(sys.argv)>1 else 'clips'
OUT = sys.argv[2] if len(sys.argv)>2 else 'Beyond_Survival_IG_4x5.mp4'
PREVIEW = os.environ.get('PREVIEW')
W,H,FPS,X = 1080,1350,30,1.2
starts=[0,13.4,29.2,43.1,57.5,70.3,85.7,96.9,114.8,133.0,153.8,174.2,196.1,208.6,221.4]
AUDIO='toma_A.mp3'; AUDIO_LEN=235.55; TAIL=4.0; END=AUDIO_LEN+TAIL
durs=[(starts[i+1] if i+1<len(starts) else END)-starts[i] for i in range(len(starts))]
os.makedirs('seg',exist_ok=True)
# overlay: bottom gradient + soft vignette
ov=Image.new('RGBA',(W,H),(0,0,0,0)); d=ImageDraw.Draw(ov)
for y in range(H):
    t=max(0,(y-H*0.50)/(H*0.50)); d.line([(0,y),(W,y)],fill=(0,0,0,int(205*min(1,t*1.25)**1.3)))
vig=Image.new('L',(W,H),0); ImageDraw.Draw(vig).ellipse([-W*0.25,-H*0.2,W*1.25,H*1.2],fill=255)
vig=vig.filter(ImageFilter.GaussianBlur(160)); va=Image.new('RGBA',(W,H),(0,0,0,0)); va.putalpha(vig.point(lambda p:int((255-p)*0.5)))
Image.alpha_composite(ov,va).save('overlay.png')
def seg(i):
    dur=durs[i]; L=dur+(X if i<len(durs)-1 else 0); f=max(1.0,L/14.9)
    out=f'seg/{i+1:02d}.mp4'
    if os.path.exists(out) or not os.path.exists(f'{CLIPDIR}/{i+1:02d}.mp4'): return
    slow=f'setpts={f:.4f}*PTS,' if f>1 else ''
    interp=('minterpolate=fps=30:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1' if (f>1.05 and not PREVIEW) else f'fps={FPS}')
    vf=f'scale={W}:-2:flags=lanczos,crop={W}:{H}:0:{'(ih-'+str(H)+')' if i==1 else '(ih-'+str(H)+')/2'},{'eq=brightness=0.05:gamma=1.35:saturation=1.1,' if i==1 else ''}{slow}{interp},fps={FPS},trim=0:{L:.3f},setpts=PTS-STARTPTS,setsar=1,format=yuv420p'
    subprocess.run(['ffmpeg','-y','-loglevel','error','-i',f'{CLIPDIR}/{i+1:02d}.mp4','-vf',vf,'-an','-c:v','libx264','-preset','veryfast','-crf','14','-threads','2',out],check=True)
    print('seg',i+1,'f=%.2f'%f,flush=True)
with ThreadPoolExecutor(2) as ex: list(ex.map(seg,range(len(durs))))
if os.environ.get('STAGE1_ONLY'): sys.exit(0)
inputs=[];filters=[]
for i in range(len(durs)): inputs+=['-i',f'seg/{i+1:02d}.mp4']
prev='0:v'
for i in range(1,len(durs)):
    filters.append(f'[{prev}][{i}:v]xfade=transition=fade:duration={X}:offset={starts[i]-X/2:.3f}[x{i}]'); prev=f'x{i}'
n=len(durs)
filters.append(f'[{prev}]trim=0:{END:.3f},fade=t=in:st=0:d=1.0,fade=t=out:st={END-2.5:.3f}:d=2.5[base]')
filters.append(f'[{n+1}:v]format=rgba[ov];[base][ov]overlay=0:0:shortest=0,noise=alls=3:allf=t,ass=subs.ass:fontsdir=fonts,format=yuv420p[vout]')
filters.append(f'[{n}:a]apad,atrim=0:{END:.3f},afade=t=out:st={END-2.0:.3f}:d=2.0,loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000[aout]')
inputs+=['-i',AUDIO,'-loop','1','-framerate',str(FPS),'-i','overlay.png']
T=PREVIEW or f'{END:.3f}'
cmd=['ffmpeg','-y','-hide_banner','-loglevel','error']+inputs+['-filter_complex',';'.join(filters),'-map','[vout]','-map','[aout]',
     '-c:v','libx264','-preset','medium','-crf','19','-maxrate','14M','-bufsize','28M','-profile:v','high','-level','4.2','-pix_fmt','yuv420p','-r',str(FPS),
     '-c:a','aac','-b:a','192k','-movflags','+faststart','-t',T,OUT]
print('durations',[round(x,1) for x in durs],flush=True); subprocess.run(cmd,check=True); print('done',OUT)

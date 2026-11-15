"""Beyond Survival v2: 28 narrative shots + voice + ducked score -> 1080x1350 IG feed video."""
import subprocess, sys, os
from concurrent.futures import ThreadPoolExecutor
W,H,FPS,X = 1080,1350,30,0.8
AUDIO='toma_A.mp3'; MUSIC='musica_completa.wav'; END=239.55
OUT=sys.argv[1] if len(sys.argv)>1 else 'Beyond_Survival_v2_IG_4x5.mp4'
STAGE1_ONLY=os.environ.get('STAGE1_ONLY')
# (start_time, source clip, offset_in_clip_seconds)
SHOTS=[(0.0,'v2/clips/01.mp4',0),(7.5,'clips/01.mp4',4),(13.4,'v2/clips/03.mp4',0),(21.3,'clips/02.mp4',3),
 (29.2,'v2/clips/05.mp4',0),(36.9,'v2/clips/06.mp4',0),(43.1,'clips/04.mp4',2),(50.0,'v2/clips/08.mp4',0),
 (57.5,'clips/05.mp4',3),(64.0,'v2/clips/10.mp4',0),(70.3,'v2/clips/11.mp4',0),(75.9,'clips/07.mp4',2),
 (85.7,'v2/clips/13.mp4',0),(96.9,'v2/clips/14.mp4',0),(105.3,'v2/clips/15.mp4',0),(114.8,'v2/clips/16.mp4',0),
 (124.3,'clips/06.mp4',3),(133.0,'v2/clips/18.mp4',0),(146.8,'v2/clips/19.mp4',0),(153.8,'clips/11.mp4',2),
 (163.0,'v2/clips/21.mp4',0),(174.2,'clips/12.mp4',1),(185.8,'v2/clips/23.mp4',0),(196.1,'v2/clips/24.mp4',0),
 (208.6,'v2/clips/25.mp4',0),(215.0,'clips/14.mp4',4),(221.4,'v2/clips/27.mp4',0),(231.4,'clips/15.mp4',4)]
starts=[s for s,_,_ in SHOTS]
durs=[(starts[i+1] if i+1<len(starts) else END)-starts[i] for i in range(len(starts))]
os.makedirs('v2/seg',exist_ok=True)
def probe(f): return float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',f]))
def seg(i):
    st,src,off=SHOTS[i]; out=f'v2/seg/{i+1:02d}.mp4'
    if os.path.exists(out) or not os.path.exists(src): return
    L=durs[i]+(X if i<len(SHOTS)-1 else 0); avail=probe(src)-off-0.1
    f=max(1.0,L/avail)
    ember = src=='clips/02.mp4'
    crop_y=f'(ih-{H})' if (ember or src=='v2/clips/24.mp4') else f'(ih-{H})/2'
    eq='eq=brightness=0.05:gamma=1.35:saturation=1.1,' if ember else ''
    slow=f'setpts={f:.4f}*PTS,' if f>1 else ''
    interp='minterpolate=fps=30:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1' if f>1.05 else f'fps={FPS}'
    vf=f'scale={W}:-2:flags=lanczos,crop={W}:{H}:0:{crop_y},{eq}{slow}{interp},fps={FPS},trim=0:{L:.3f},setpts=PTS-STARTPTS,setsar=1,format=yuv420p'
    subprocess.run(['ffmpeg','-y','-loglevel','error','-ss',str(off),'-i',src,'-vf',vf,'-an','-c:v','libx264','-preset','veryfast','-crf','14','-threads','2',out],check=True)
    print('seg',i+1,'f=%.2f'%f,flush=True)
with ThreadPoolExecutor(2) as ex: list(ex.map(seg,range(len(SHOTS))))
if STAGE1_ONLY: sys.exit(0)
missing=[i+1 for i in range(len(SHOTS)) if not os.path.exists(f'v2/seg/{i+1:02d}.mp4')]
assert not missing, f'missing segments {missing}'
inputs=[];F=[]
for i in range(len(SHOTS)): inputs+=['-i',f'v2/seg/{i+1:02d}.mp4']
prev='0:v'
for i in range(1,len(SHOTS)):
    F.append(f'[{prev}][{i}:v]xfade=transition=fade:duration={X}:offset={starts[i]-X/2:.3f}[x{i}]'); prev=f'x{i}'
n=len(SHOTS)
F.append(f'[{prev}]trim=0:{END:.3f},fade=t=in:st=0:d=1.0,fade=t=out:st={END-2.5:.3f}:d=2.5[base]')
F.append(f'[{n+2}:v]format=rgba[ov];[base][ov]overlay=0:0:shortest=0,noise=alls=3:allf=t,ass=subs.ass:fontsdir=fonts,format=yuv420p[vout]')
# audio: voice normalized, music ducked under voice, mixed, final loudness
F.append(f'[{n}:a]aresample=48000,apad,atrim=0:{END:.3f},loudnorm=I=-16:TP=-2:LRA=11,asplit=2[vo][key]')
F.append(f'[{n+1}:a]aresample=48000,atrim=0:{END:.3f},loudnorm=I=-24:TP=-4:LRA=14[mu]')
F.append('[mu][key]sidechaincompress=threshold=0.02:ratio=5:attack=60:release=900:makeup=1[mud]')
F.append(f'[vo][mud]amix=inputs=2:normalize=0:duration=first,afade=t=out:st={END-2.5:.3f}:d=2.5,loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000[aout]')
inputs+=['-i',AUDIO,'-i',MUSIC,'-loop','1','-framerate',str(FPS),'-i','overlay.png']
cmd=['ffmpeg','-y','-hide_banner','-loglevel','error']+inputs+['-filter_complex',';'.join(F),'-map','[vout]','-map','[aout]',
 '-c:v','libx264','-preset','medium','-crf','19','-maxrate','14M','-bufsize','28M','-profile:v','high','-level','4.2','-pix_fmt','yuv420p','-r',str(FPS),
 '-c:a','aac','-b:a','192k','-ac','2','-movflags','+faststart','-t',f'{END:.3f}',OUT]
print('durations',[round(x,1) for x in durs],flush=True); subprocess.run(cmd,check=True); print('done',OUT)

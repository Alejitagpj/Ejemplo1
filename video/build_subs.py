import json,re
al=json.load(open('meta_D03hjUcLtSiXCuJL8P3e.json'))['alignments']['alignment']
chars=al['characters']; st=al['character_start_times_seconds']
s=''.join(chars)
AUDIO_END=235.5
# words with start times
words=[(m.group(),st[m.start()]) for m in re.finditer(r'\S+',s)]
# drop the spoken title (shown as a title card)
assert words[0][0]=='Beyond' and words[1][0]=='Survival'
words=words[2:]
# chunk by clauses, merge short ones, split long ones; max ~62 chars, shown on up to 2 lines
clauses=[];cur=[]
for w,t in words:
    cur.append((w,t))
    if re.search(r'([,.?!:;]|\.\.\.)$',w): clauses.append(cur);cur=[]
if cur: clauses.append(cur)
L=lambda c:len(' '.join(w for w,_ in c))
def split_long(c):
    if L(c)<=62: return [c]
    n=max(2,-(-L(c)//56)); target=L(c)/n; parts=[];p=[]
    for x in c:
        p.append(x)
        if L(p)>=target and len(parts)<n-1: parts.append(p);p=[]
    if p: parts.append(p)
    # avoid dangling 1-word part
    if len(parts)>1 and len(parts[-1])==1: parts[-2]+=parts[-1]; parts.pop()
    return parts
pieces=[q for c in clauses for q in split_long(c)]
out=[]
for c in pieces:
    if out and L(out[-1])+L(c)+1<=50 and not re.search(r'[.?!:]$|\.\.\.$',out[-1][-1][0]):
        out[-1]=out[-1]+c
    else: out.append(c)
def wrap(c):
    ws=[w for w,_ in c]; txt=' '.join(ws)
    if len(txt)<=30: return txt
    best=None
    for i in range(1,len(ws)):
        a=' '.join(ws[:i]); b=' '.join(ws[i:]); sc=abs(len(a)-len(b))
        if best is None or sc<best[0]: best=(sc,a,b)
    return best[1]+'\\N'+best[2]
def ts(x):
    h=int(x//3600);m=int(x%3600//60);s_=x%60;return f"{h}:{m:02d}:{s_:05.2f}"
lines=[]
for i,c in enumerate(out):
    a=c[0][1]-0.05
    b=(out[i+1][0][1]-0.08) if i+1<len(out) else AUDIO_END
    b=min(b, a+max(1.2, 0.38*len(c)+1.8))  # don't linger through long pauses
    txt=wrap(c)
    lines.append((a,b,txt))
hdr="""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1350
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Sub,Cormorant Garamond SemiBold,72,&H00F7F4EF,&H00FFFFFF,&H8C000000,&H78000000,0,0,0,0,100,100,0.8,0,1,2.6,0,2,80,80,150,1
Style: Title,Cormorant Garamond SemiBold,104,&H00F4F1EC,&H00FFFFFF,&H50000000,&H80000000,0,0,0,0,100,100,6,0,1,1.5,3,5,60,60,0,1
Style: Tag,Cormorant Garamond Medium,44,&H00D9E6F0,&H00FFFFFF,&H50000000,&H80000000,0,1,0,0,100,100,2,0,1,1,2,5,60,60,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
ev=[f"Dialogue: 1,{ts(0.3)},{ts(2.9)},Title,,0,0,0,,{{\\fad(600,500)}}Beyond Survival"]
for a,b,t in lines:
    ev.append(f"Dialogue: 0,{ts(a)},{ts(b)},Sub,,0,0,0,,{{\\fad(180,180)\\blur0.8}}{t}")
open('subs.ass','w').write(hdr+'\n'.join(ev)+'\n')
print(len(lines),'subtitle lines'); [print(f"{a:6.1f}-{b:6.1f} {t}") for a,b,t in lines[:12]]; print('...'); [print(f"{a:6.1f}-{b:6.1f} {t}") for a,b,t in lines[-6:]]

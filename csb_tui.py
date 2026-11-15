#!/usr/bin/env python3
# csb_tui - CubeSandbox CLI: the terminal UI. It renders only; the command layer is csb.py.
import ast,os,sys,re,json,select,termios,tty,shlex,subprocess,time,textwrap,shutil,threading,base64,io,signal,tempfile
import unicodedata as _ud

CLI=os.path.dirname(os.path.abspath(__file__));HOME=os.path.expanduser('~')
sys.path.insert(0,CLI)
import csb
def h2t(h):
    if isinstance(h, tuple): return h
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
def hexs(t): return '%02x%02x%02x' % t
BOLD, BOFF, FG0, RST = '\x1b[1m', '\x1b[22m', '\x1b[39m', '\x1b[0m'
ANSI = re.compile(r'\x1b\[[0-9;]*m')
def _noc():
    return bool(os.environ.get('NO_COLOR'))or(os.environ.get('TERM')or'').strip().lower()=='dumb'
def _fg24(c): return '\x1b[38;2;%d;%d;%dm' % h2t(c)
def _bg24(c): return '\x1b[48;2;%d;%d;%dm' % h2t(c)
_CDEF='24'
_P8=((0,0,0),(205,0,0),(0,205,0),(205,205,0),(0,0,238),(205,0,205),(0,205,205),(229,229,229))
_P16=_P8+((127,127,127),(255,0,0),(0,255,0),(255,255,0),(92,92,255),(255,0,255),(0,255,255),(255,255,255))
_P256=((0,0,0),(128,0,0),(0,128,0),(128,128,0),(0,0,128),(128,0,128),(0,128,128),(192,192,192),
 (128,128,128),(255,0,0),(0,255,0),(255,255,0),(0,0,255),(255,0,255),(0,255,255),(255,255,255))+tuple(
 (r,g,b)for r in(0,95,135,175,215,255)for g in(0,95,135,175,215,255)for b in(0,95,135,175,215,255))+tuple(
 (8+10*i,)*3 for i in range(24))
_PAL={8:_P8,16:_P16,256:_P256}
_POOR=re.compile(r'^(xterm|screen|tmux|linux|vt\d+|ansi|cons\d+|cygwin|rxvt.*|st|eterm.*|sun|putty)$')
_QBH=[None]
def _cdet(t,c):
    if c in('truecolor','24bit'):return 24
    if '256color' in t:return 256
    if '16color' in t:return 16
    return 8 if _POOR.match(t)else 24
def _cdepth_v(vc,vt,t,tp='',uv=None):
    v=(vc or'').strip().lower()
    if v:return _cdet(t,vt)if v=='auto'else(int(v)if v in('8','16','256')else 24)
    u=(uv or'').strip().lower()
    if u:
        if u=='auto':return _cdet(t,vt)
        if u in('8','16','256','24'):return int(u)
    d=csb._TPREF.get((tp or'').strip().lower())
    return d[1]if d and d[1]else 24
def _cdepth():
    return _cdepth_v(csb._sw('ui_color'),csb._ev('COLORTERM'),csb._ev('TERM'),csb._ev('TERM_PROGRAM'),None)
def _d2(a,b): return(a[0]-b[0])**2+(a[1]-b[1])**2+(a[2]-b[2])**2
def _qi(t,d):
    p=_PAL[d]
    return min(range(len(p)),key=lambda i:_d2(p[i],t))
def _qfg(t,h,d):
    p=_PAL[d];r=((hexs(p[_qi(h2t(h),d)]),)if h is not None else('000000','ffffff'))
    n=[i for i in range(len(p))if max(p[i])-min(p[i])<=8]
    order=sorted(range(len(p)),key=lambda i:_d2(p[i],t))
    for cand in((order if max(t)-min(t)>24 else n+[i for i in order if i not in n]),order):
        for i in cand:
            if all(_cr(hexs(p[i]),x)>=MIN_CR for x in r):return i
    return _qi(t,d)
def _fgesc(c,d,h): return _fg24(c)if d==24 else'\x1b[38;5;%dm'%_qfg(h2t(c),h,d)
def _bgesc(c,d): return _bg24(c)if d==24 else'\x1b[48;5;%dm'%_qi(h2t(c),d)
def _fgc(c): return _fgesc(c,_cdepth(),_QBH[0])
def _bgc(c):
    _QBH[0]=c
    return _bgesc(c,_cdepth())
def fgc(c): return ''if _noc()else _fgc(c)
def bgc(c): return ''if _noc()else _bgc(c)
def vw(s) -> int:
    _z=_MARKS
    return sum(0 if c in _z or _ud.category(c)in('Mn','Me','Cf')else(2 if _ud.east_asian_width(c)in'WF' else 1)for c in ANSI.sub('',s))
def _fit(t,w):
    n=vw(t)
    if n<=w:return t,' '*(w-n)
    while t and vw(t)>w:t=t[:-1]
    return t,' '*(w-vw(t))

def R(W, p, segs):
    cells, tot = [], 0
    for s in segs:
        w, t, role = s[0], s[1], s[2]
        bold = s[3] if len(s) > 3 else False
        _r = s[4] if len(s) > 4 else 'bg'
        bg = _bg(p) if _r == 'bg' else p[_r]
        if role == 'RAW':
            cells.append(bgc(bg) + t + FG0 + ' ' * max(0, w - vw(t)))
        else:
            _t,_pad=_fit(_san(t),w)
            cells.append(bgc(bg) + fgc(p[role]) + (BOLD if bold else '') + _t + BOFF + FG0 + _pad)
        tot += w
    assert tot == W, 'frame width %d != %d' % (tot, W)
    _l=''.join(cells) + RST
    return _l.translate(_TBL) if _TBL else _l

def paint(txt, p, bgrole, flip=False, stroke=None, line=None):
    stroke = stroke or (p['shadow'] if flip else p['accent'])
    line = line or (p['accent'] if flip else p['shadow'])
    o = ''
    for ch in txt:
        o += fgc(line if ch == '_' else (stroke if ch in '\\/' else(_bg(p) if bgrole == 'bg' else p[bgrole]))) + ch
    return o

SWP_WB=csb._sw('tui_sweep_wb')
SWP_FRAMES=csb._sw('tui_sweep_frames')
SWP_TICK=csb._sw('tui_sweep_tick')
SWP_SEC=csb._sw('tui_sweep_sec')
SWP_ON=not csb._sw('ui_no_sweep')
def _sweep(raw,ph,wb,LW):
    half=ph<0.5;q=ph*2 if half else(ph-0.5)*2;P=q*(LW+wb)-wb/2
    flat=(lambda i:i<P)if half else(lambda i:i>=P);a=int(P-wb/2)
    return ''.join('_'if flat(i)and ch in'\\/'else ch for i,ch in enumerate(raw)),(a,a+wb)
def _sweep_paint(txt,p,stroke,line,beam,bgrole='bg'):
    stroke=stroke or p['shadow'];line=line or p['accent']
    a,b=beam;b0=_bg(p)if bgrole=='bg'else p[bgrole];bc=p.get('panel')or b0;o=''
    for i,ch in enumerate(txt):
        ib=a<=i<b;c=line if ch=='_'else(stroke if ch in'\\/'else b0)
        o+=bgc(bc if ib else b0)+fgc(p['fg']if(ib and ch=='_')else c)+ch
    return o+FG0
def seg(w, label, ch, p, role='accent', bg='bg'):
    _lw=vw(label) if label else 0
    if not label or w < _lw + 3: return [(w, ch * w, 'frame', False, bg)]
    return [(1, ch, 'frame', False, bg), (_lw + 2, ' ' + label + ' ', role, True, bg),
            (w - _lw - 3, ch * (w - _lw - 3), 'frame', False, bg)]

def sc(code, name, fam, bg, panel, fg, frame, sub, accent, warn, selbg, shadow, note, logo=None, ttl=None, hswap=False):
    return dict(code=code, name=name, fam=fam, bg=bg, panel=panel, fg=fg, frame=frame, sub=sub,
                accent=accent, warn=warn, selbg=selbg, shadow=shadow, note=note, logo=logo, ttl=ttl or accent,
                hswap=hswap)

FIN = '★ design locked'
ROSE = 'dd569c'
ORIG = '8f34c8'
VERM = 'ef6a4a'
AMBER = 'ff7500'
FAB = 'fab403'
CREAM = 'ffc373'
SCH = [
 sc('D02', 'Black · pure paper white·inverted', FIN, '000000', '111111', 'ffffff', 'ffffff', 'aaaaaa', 'ffffff', 'ffffff', 'ffffff', 'ffffff',
    'White text on black; logo strokes #ffffff, line = the command bar inactive colour #aaaaaa (sub); no red anywhere ([D]/[E] are told apart by their marker)',
    logo=('ffffff', 'aaaaaa')),
 sc('D04o', 'Purple · rose pink original', FIN, '150c20', '1a0f28', 'e5e8e9', ROSE, ORIG, ROSE, 'fab403', ROSE, ORIG,
    'Purple ground, rose pink: logo **font purple #%s** (the design csb-purple.py original value), line #%s; frame and accent #%s, warning gold #fab403.'
    '(2026-09-15: one step pinker - only frame/accent/selbg changed #c15c9c→#%s, the two logo colours went back to the design;'
    'an earlier revision that swapped the stroke and line colours was reverted)' % (ORIG, ROSE, ROSE, ROSE),
    logo=(ORIG, ROSE)),
 sc('D14', 'Amber · true orange·warm cream text', FIN, '1a1005', '241708', CREAM, AMBER, 'b8822f', AMBER, VERM, AMBER, '8a5a10',
    'Amber family (sixth revision): accent / selbg / **frame** unified = #%s (old values accent #fab403→#ffc94d→#ff9f1c, frame #8a5a10);'
    'logo strokes, the title line "CSB · …" and the version number **#%s = accent = the [T] template line text colour** (the rule is that all three follow the template text colour;'
    'the design amber #fab403 is kept for the record only), logo line #%s; warning colour = light vermilion #%s.'
    '(2026-09-15 fourth revision: starting from the original amber gold and pushing further toward orange, lightness unchanged throughout - the brightest text fg #fff1d6→#fff8ec→'
    '#ffe8c4→#%s (saturation 16.1%%→7.5%%→23.1%%→45.9%%, hue 39.5°→37.9°→36.6°→36.9°);'
    'accent/selbg #fab403→#ffc94d→#ff9f1c→#e98e18→#%s; the second revision #fff8ec / #ffc94d, the third #ffe8c4 and the fourth #ffd28a are all withdrawn;'
    'the old frame value #8a5a10 is kept here for the record; the old logo stroke #%s (design amber) is also kept for the record.'
    'the secondary text colour (sub) went #c98a3a→#b8822f when the accent moved e98e18→ff7500. '
    'help swaps the colours of the attribute column and of the footer labels (the nodes/notes/skins three lines) (hswap=True))' % (AMBER, AMBER, 'b8822f', VERM, CREAM, AMBER, FAB),
    logo=(AMBER, '8a5a10'), hswap=True),
 sc('D03', 'Green · green black·lime text', FIN, '000000', '0a0a0a', 'cbfa32', '00ff41', '6b7a2a', '00ff41', '00f400', '00ff41', '009927',
    'Lime on black: frame and the [T] template line share #00ff41 (accent), sandbox line #cbfa32 (fg), snapshot line #6b7a2a (sub);'
    'logo strokes #00ff41, line #6b7a2a = sub (chosen to match an inactive command-bar command;'
    'the design original #009927 is kept here for the record)',
    logo=('00ff41', '6b7a2a')),
 sc('D01', 'White · pure paper white', FIN, 'ffffff', 'f2f2f2', '000000', '000000', '6e6e6e', '000000', '000000', '000000', '373737',
    'Black text on white, no decoration, the safest fallback; logo strokes #373737, line #000000 (the design has logo=None ⇒ the paint() default = shadow/accent,, changed back from sub #6e6e6e)',
    logo=('373737', '000000')),
]
_BGR = 'panel' if csb._sw('ui_panel_bg') else 'bg'
def _bg(p):return p.get(_BGR)or p['bg']
CSB = os.path.join(CLI, 'csb.py')
def _src():
    try:
        with open(CSB, encoding='utf-8') as f:t = f.read()
    except OSError:
        return ['CSB'], 'csb v'+csb.__version__
    art = None
    try:
        for nd in ast.parse(t).body:
            if isinstance(nd, ast.Assign) and any(getattr(tg, 'id', None) == 'LOGO' for tg in nd.targets):
                art = str(ast.literal_eval(nd.value)).split('\n')
                break
    except Exception:
        art = None
    if not art:
        m0 = re.search(r"^LOGO = r'''(.*?)'''", t, re.S | re.M)
        art = m0.group(1).split('\n') if m0 else ['CSB']
    m = re.search(r"^__version__\s*=\s*['\"]([^'\"]+)['\"]", t, re.M)
    return art, 'csb v' + (m.group(1) if m else '0.1.1')

ART, VER = _src()
LW = max(len(x) for x in ART)

CMD = ['s start', 'f commit', 'c clone', 'B build', 'V volume', 'T theme', 'e exec', 'i shell',
       'n snap', 'b rb', 'o logs', 'p pause', 'u resume', 't timeout', 'k kill', 'd clean',
       'l label-reset', 'm mark', 'M range', '? help', 'q quit', 'z fold', 'v fold-all',
       'a alias', 'A adopt', '/ filter']
CONST=('cmd','help','quit','build','volume','theme','fold','fold-all','filter')
UND='\x1b[4m';UNDOFF='\x1b[24m'
ANIM=0.035
VER_ANIM=ANIM*3
_ASC=csb._box_ascii()
K_R={'tl':'+','tr':'+','bl':'+','br':'+','h':'-','v':'|','jl':'+','jr':'+'}if _ASC else \
    {'tl':'┏','tr':'┓','bl':'┗','br':'┛','h':'━','v':'┃','jl':'┣','jr':'┫'}
ANSI=ANSI;vw=vw;from functools import lru_cache
_qfg=lru_cache(maxsize=8192)(_qfg);_fgesc=lru_cache(maxsize=8192)(_fgesc);_bgesc=lru_cache(maxsize=8192)(_bgesc);R=R;paint=paint;seg=seg
BOLD,BOFF,FG0,RST=BOLD,BOFF,FG0,RST
KCLR='\x1b[K'
VERN='csb v'+csb.__version__

def _one(x,n=0):
    x=csb._nump(x)
    if csb._net_hint(str(x)):x='%s: cannot reach the server - check CUBE_API_URL, or that the API is up'%str(x).split(':',1)[0]
    x=_san(' '.join(str(x).split()))
    return _cut(x,n)if n and n>0 else x
def _emptytree(u):
    if u.flt:return 'filter \'%s\' matches nothing - press / then Enter to clear it'%u.flt
    return 'no nodes - no templates yet (press B to build one)'
FW=3.0
GU=60.0
TUI_POLL=csb._sw('cube_tui_poll')
class _FOut:
    def __init__(s,real,buf):s.r=real;s.b=buf;s.th=threading.get_ident()
    def write(s,x):(s.b if threading.get_ident()==s.th else s.r).write(x);return len(x)
    def flush(s):
        try:s.r.flush()
        except Exception:pass
    def __getattr__(s,k):return getattr(object.__getattribute__(s,'r'),k)
def _fet_secs():return csb._sw('cube_fetch_wait')
def _gsecs():return csb._sw('cube_fetch_giveup')
def _fjob(fn):
    buf=io.StringIO();b={'s':buf};o=[sys.stdout,sys.stderr]
    def go():
        so=_FOut(o[0],buf);se=_FOut(o[1],buf);sys.stdout,sys.stderr=so,se
        try:b['v']=fn()
        except BaseException as e:b['e']=e
        finally:
            if sys.stdout is so:sys.stdout=o[0]
            if sys.stderr is se:sys.stderr=o[1]
    th=threading.Thread(target=go,daemon=True);th.start()
    return {'th':th,'b':b,'t0':time.monotonic()}
def _fcall(fn):
    j=_fjob(fn);j['th'].join(_fet_secs())
    return (not j['th'].is_alive()),j['b']
def _vol_rows(u):
    ok,b=_fcall(lambda:csb.vol_rows(u.c))
    if ok and 'e' not in b:return b.get('v')
    u.status='volumes unavailable'
    return None
def _tpl_rows(u):
    ok,b=_fcall(lambda:csb.tpl_rows(u.c))
    if ok and 'e' not in b:return [t for t in(b.get('v')or[])if not t.get('is_snap')]
    u.status='templates from local records'
    return []
def _autohide_ask(t,u,draw):
    q=tui_autohide_pending()
    if not q:return
    body,ch=tui_autohide_ask(q['gone'],q['rows'],q['total'])
    v,_k=pick(t,'%d local entries are not in the server list'%len(q['gone']),[(ch[0],'keep'),(ch[1],'hide')],
              u,draw,pre=body,sel=0)
    n=tui_autohide_answer(v=='hide')
    if n:u.status='hid %d stale entries'%n;u.fetch(0,again=True)
class UI:
    def __init__(s,c=None):
        s.c=c or csb.cfg();s.sel=0;s.top=0;s.status='ready';s.msg='';s.marked=set();s.folded=set();s.anch=None;s.atyp=None;s.pin={}
        s.flt='';s.rows=[];s.st={};s.groups=set();s.fold_ok=False;s.ki='5';s.skin=s._load();s.modal=None;s.hmode=False;s.hoff=0;s.job=None;s.wait=0.0;s.foldpend=False;s.netdown=False;s.markdrop=0
    def _load(s):return tui_theme_cur(s.c)
    def next_skin(s):
        s.skin=tui_theme_step(s.c,s.skin)
        try:_e=tui_theme_err()
        except Exception:_e=None
        if _e:s.status='skin %s - could not save the theme (%s), it will not survive a restart'%(s.skin,_e)
        return s.skin
    def sc(s):return [x for x in SCH if x['code']==s.skin][0]
    def fetch(s,lim=None,again=False):
        t0=time.monotonic()
        if s.job is not None and not again and t0-s.job['t0']>=_gsecs():again=True
        if s.job is None or again:s.job=_fjob(s._fetch);s.last_fetch=t0
        j=s.job;j['th'].join(_fet_secs() if lim is None else max(0.0,lim))
        if j['th'].is_alive():s.wait=j['t0'];return False
        s.job=None;s.wait=0.0;s.last_fetch=time.monotonic();s._land(j)
        return True
    def poll(s):
        j=s.job
        if j is None:s.wait=0.0;return False
        if j['th'].is_alive():s.wait=j['t0'];return False
        s.job=None;s.wait=0.0;s._land(j)
        return True
    def _land(s,j):
        b=j['b'];_so=b['s'].getvalue()
        if 'e' in b:
            e=b['e'];s.msg=_one('fetch failed: %s'%(_so or(('exit %s'%(e.code,))if isinstance(e,SystemExit)else e)));s.netdown=True
        elif _so.strip():s.msg=_one(_so)
        v=b.get('v')
        if v:
            _fl0=set(v.get('fl0') or ());s.netdown=False;s.msg='' if (s.msg or '').startswith('fetch failed:') else s.msg
            if _fl0!=set(s.folded):
                _keep=set(s.folded)
                s._apply(v)
                s.folded=_keep
                s.refold()
            else:s._apply(v)
        if getattr(s,'foldpend',False) and s.refold():s.foldpend=False
    def _fetch(s):
        tps=csb.tpl_rows(s.c);sbs=csb.fetch_sbs(s.c);lg=csb.led(s.c)
        st=tui_stats(sbs,tps,lg)
        gp=set();fl=set(s.folded);fl0=frozenset(s.folded)
        rows,err,fold_ok=tui_flat(s.c,fl,s.flt,gp,getattr(s,'fold_ok',False),dict(s.pin))
        return {'rows':rows,'why':err,'fl':fl,'fo':fold_ok,'gp':gp,'st':st,'fl0':fl0}
    def _anchor(s):
        p=s.cur()
        return ((p or{}).get('id'),(p or{}).get('family'),s.sel,_kindof(p))
    def _apply(s,g):
        _a=s._anchor()
        s.st=g['st'];s.groups=g['gp'];s.fold_ok=g['fo']
        s.rows=g['rows']if g['rows']or not g['why']else s.rows
        s.folded|=g['fl']
        if g['why']:s.msg=g['why']
        if s.rows:s.sel=_reselect(s.rows,*_a)
    def refold(s):
        t=csb._LASTRT[0]
        if t is None:return False
        gp=set();fl=set(s.folded)
        rows,err,fo=tui_flat(None,fl,s.flt,gp,getattr(s,'fold_ok',False),dict(s.pin),tree=t)
        s._apply({'rows':rows,'why':err,'fl':fl,'fo':fo,'gp':gp,'st':s.st})
        return True
    def refold_or_fetch(s):
        if s.refold():return True
        s.foldpend=True
        return False
    def cur(s):return s.rows[s.sel][1] if s.rows and s.sel<len(s.rows) else None
    def arg(s):
        n=s.cur();return (n.get('arg')or n.get('id')or n.get('label')) if n and n.get('id') else None
    def on(s,n):
        return tui_on(n)
def _hint(rows,i):
    return 0<=i<len(rows) and tui_hint(rows[i][1])
def _step(rows,i,d):
    n=len(rows)
    if not n:return 0
    j=max(0,min(n-1,i))
    for _ in range(abs(d)):
        k=j+(1 if d>0 else-1)
        while 0<=k<n and _hint(rows,k):k+=(1 if d>0 else-1)
        if k<0 or k>=n:break
        j=k
    return j
def _kindof(n):
    k=(n or{}).get('kind')
    return 'sb'if k in('start','clone','from-snap','unknown')else('snap'if k in('snap','snap-root')else('tpl'if k=='tpl-root'else'other'))
def _reselect(rows,pid,grp,old,kd=None):
    for i,(d,n)in enumerate(rows):
        if pid and n.get('id')==pid and not _hint(rows,i):return i
    if grp:
        same=[i for i,(d,n)in enumerate(rows)if(n.get('family')or n.get('label'))==grp]
        if same:
            _p=[i for i in same if not _hint(rows,i)and(kd is None or _kindof(rows[i][1])==kd)]
            if _p:return min(_p,key=lambda i:abs(i-old))
            _q=[i for i in same if not _hint(rows,i)]
            return min(_q,key=lambda i:abs(i-old))if _q else min(same,key=lambda i:abs(i-old))
    old=max(0,min(old,len(rows)-1))
    for _d in(1,-1):
        for i in (range(old,len(rows))if _d>0 else range(old,-1,-1)):
            if not _hint(rows,i):return i
    return old
def _focus(rows,ids):
    ids=set(ids or())
    for i,(d,n)in enumerate(rows):
        if n.get('id')in ids:return i
    return None
def _row_mark(n,k):return('[%s]'%tui_glyph(n))if k!='note'else''
def row_txt(n,d,sel):
    k=n.get('kind')
    mk=('[%s]'%tui_glyph(n))if n.get('unadopted')or n.get('nolocal')else('[T]'if k=='tpl-root'else('[s]'if k in('snap-root','snap')else('[U]'if k=='unreg'else(('[E]'if n.get('external')else'[D]')if k=='dead'else('[X]'if k=='stale'else('[S]'if k in('start','clone','from-snap','unknown')else _row_mark(n,k)))))))
    if k=='tpl-root'and n.get('deleted'):mk='[D]'
    lab=tui_name(n);_vs=[x for x in(n.get('vols')or[])if x]
    st=n.get('state')or('external'if k=='dead'and n.get('external')else('deleted'if k=='dead'else('stale'if n.get('stale')else('orphan'if n.get('orphan')else''))))
    pre=n.get('_pre','')or'  '
    if sel:pre='> '+pre[2:]
    _c=n.get('_ch');_v=n.get('_chv')
    _t='%d of %d'%(_v,_c)if _c and _v is not None and _v!=_c else'%s'%_c
    _cc=int(n.get('clonetemp')or 0)
    _dupct=k in('snap','snap-root')and _c and _cc==int(_c)
    _ct=(' (%s)%s'%(_t,' [+]'if n.get('_folded')else''))if _c and not _dupct else''
    _tg=tui_tag(n);_vt=('[VOL %s]'%(','.join(_vs[:2])+('+%d'%(len(_vs)-2)if len(_vs)>2 else'')))if _vs else''
    return pre+mk+' '+str(lab)+((' (%s)'%_tg)if _tg else'')+((' (%s)'%st)if st else'')+(' '+_vt if _vt else'')+_ct
HIT={}
def hit_test(u,x,y,hit=None):
    h=HIT if hit is None else hit
    if not h:return None
    j=(y-1)-h['body0']
    if j<0 or j>=h['body']:return None
    off=x-3
    if 0<=off<h['aw']:
        jj=j-h['pad']
        cb=h.get('cbar')or[]
        if 0<=jj<len(cb):
            part=cb[jj][off//max(1,h['cw'])]
            if part:return('key',part.split(' ',1)[0])
        return None
    if off>=h['aw']+1:
        i=u.top+j
        if 0<=i<len(getattr(u,'rows',())or()):return('node',i)
    return None
def _panw(t,hoff):
    if hoff<=0:return t
    i=0;acc=0
    while i<len(t)and acc<hoff:
        acc+=vw(t[i]);i+=1
    return t[i:]
def _tabcomplete(buf,ws,st=None):
    tok=buf.split(' ')[-1] if ' ' in buf else buf
    head=buf[:len(buf)-len(tok)]
    live=bool(st and st.get('c') and tok in st['c'])
    if not live and tok and tok in ws:return head+tok+' ',{'c':[],'i':0,'cp':''},[]
    cd=list(st['c'])if live else[w for w in ws if w.startswith(tok)]
    if not cd:return buf,{'c':[],'i':0,'cp':''},[]
    cp=os.path.commonprefix(cd)
    if len(cd)==1:return head+cd[0]+' ',{'c':[],'i':0,'cp':''},[]
    if len(cp)>len(tok):return head+cp,{'c':cd,'i':0,'cp':cp},cd
    i=(st['i']if live else 0)
    while len(cd)>1 and cd[i%len(cd)]==tok:i+=1
    w=cd[i%len(cd)]
    return head+w,{'c':cd,'i':i+1,'cp':cp},cd
def _selok(rows,i):
    if 0<=i<len(rows)and not tui_hint(rows[i][1]):return i
    for j in range(max(0,i),len(rows)):
        if not tui_hint(rows[j][1]):return j
    for j in range(min(i,len(rows))-1,-1,-1):
        if not tui_hint(rows[j][1]):return j
    return None
def _markrow(t,sel,marked):
    if not marked:return t
    return('>*'+t[2:]if sel else(' *'+t[2:]))
def _anchorlabel(rows,anch,width=24):
    if not anch:return''
    n=next((r for _d,r in rows if r.get('id')==anch),None)
    if not n:return'   [anchor off]'
    return'   [anchor %s]'%(tui_name(n)[:width])
def _sb_left(nm,dup,mk,an,pn,bud):
    for _d in('an','pn','dup'):
        t=nm+dup+mk+an+pn
        if vw(t)<=bud:return t
        if _d=='an':an=''
        elif _d=='pn':pn=''
        else:dup=''
    _r=max(0,bud-vw(mk))
    return pad2(_cut(nm,_r)if _r else'',_r)+mk
def _row_fg(t,sel,kd=None):
    if sel:return'bg'
    if kd is not None:
        if kd in('dead','stale'):return'warn'
        if kd in('snap','snap-root'):return'sub'
        if kd in('tpl-root','tpl-raw'):return'accent'
        return'fg'
    if'[D]'in t or'[E]'in t or'[X]'in t:return'warn'
    if'[s]'in t:return'sub'
    if'[T]'in t:return'accent'
    return'fg'
MINW,MINH=45,6
def _narwin(W,H,p,lines):
    K=K_R;h,v=K['h'],K['v']
    if W<8:return [' '*max(0,W)for _ in range(max(0,H))]
    inner=W-4
    blank=R(W,p,[(1,v,'frame'),(1,' ','bg'),(inner,' '*inner,'bg'),(1,' ','bg'),(1,v,'frame')])
    o=[R(W,p,[(1,K['tl'],'frame',False,'bg'),(W-2,h,'frame'),(1,K['tr'],'frame',False,'bg')])]
    mid=[blank for _ in range(max(0,H-2))]
    top=max(0,(len(mid)-len(lines))//2)
    for i,t in enumerate(lines):
        if top+i<len(mid):
            t=_cut(t,inner);pad=max(0,(inner-vw(t))//2)
            mid[top+i]=R(W,p,[(1,v,'frame'),(1,' ','bg'),(inner,' '*pad+t+' '*max(0,inner-pad-vw(t)),'warn'),(1,' ','bg'),(1,v,'frame')])
    o+=mid
    o.append(R(W,p,[(1,K['bl'],'frame'),(W-2,h,'frame'),(1,K['br'],'frame')]))
    while len(o)<H:o.insert(max(1,len(o)-1),blank)
    return o[:H]if H>=2 else o[:max(0,H)]
def view(u,ki,sc,W,H,stage=4,nlogo=9,nrow=None,nver=None):
    p=dict(sc);K=K_R;h,v=K['h'],K['v']
    aw,inner=32,W-4;bw=inner-aw-1;off=max(0,(inner-LW)//2)
    HIT.clear()
    if W<MINW or H<MINH:
        _w=_narwin(W,H,p,['%dx%d - needs %dx%d'%(W,H,MINW,MINH),'csb needs a bigger window','resize or use the CLI'])
        return list(_w)
    _st=getattr(u,'st',None)or{}
    sbn=_st.get('S',0);run=_st.get('running',0)
    title=('CSB · cannot reach the server'if getattr(u,'netdown',False)else'CSB · %d Sandbox%s (%d Running)'%(sbn,''if sbn==1 else'es',run))
    if getattr(u,'flt',None):title+='  [filter: %s]'%u.flt
    o=[R(W,p,[(1,K['tl'],'frame',False,'bg')]+seg(W-2,title,h,p,role='ttl',bg='bg')+[(1,K['tr'],'frame',False,'bg')])]
    assert len(o)==1
    _need=max(0,fixed_rows(H)-H)
    _blank=0 if _need>0 else 1
    _lg=9 if _need<=1 else max(0,9-(_need-1))
    _shed=(1-_blank)+(9-_lg)
    _mt=getattr(u,'msg','')or getattr(u,'status','')or''
    _mt=''if not isinstance(_mt,str)else _mt
    _mk=('   [marked: %d]'%len(getattr(u,'marked',())or()))if getattr(u,'marked',None)else''
    _mkw=vw(_mk)
    _mroom=max(8,inner-_mkw)
    _ms=bool(stage>=4 and _mt and vw(_mt)>_mroom-4)
    _ls0=(_wrapdw(_mt,_mroom)or[''])if _ms else[]
    _want=next((i+1 for i,x in enumerate(_ls0)if x.rstrip().endswith(('.','!','?',':',';'))),len(_ls0))if _ls0 else 0
    _pay=min(max(len(_ls0)-1,_want-1),4)if _ls0 else 0
    if _pay>max(0,H-fixed_rows(H)+_shed):
        _k=min(_pay-max(0,H-fixed_rows(H)+_shed),_lg);_lg-=_k;_shed+=_k
    if _blank:o.append(R(W,p,[(1,v,'frame'),(1,' ','bg'),(inner,' '*inner,'bg'),(1,' ','bg'),(1,v,'frame')]))
    nl=min(min(9,max(0,nlogo))if stage>=2 else 0,_lg)
    _n=len(VERN)if nver is None else max(0,min(int(nver),len(VERN)))
    _vs=VERN if nver is None else(VERN[:_n]if stage>=5 else'')
    _sw=getattr(u,'swp',None)
    for i in range(_lg):
        _a=ART[i]if i<len(ART)else''
        raw=_a[:inner]if inner<len(_a)else _a
        if nl and _sw is not None and i<nl:
            _t,_bm=_sweep(raw,_sw,SWP_WB,len(raw))
            m=_sweep_paint(' '*off+_t+' '*(inner-off-len(_t)),p,*((sc['logo']or(None,None))),(_bm[0]+off,_bm[1]+off))
        else:
            m=(paint(' '*off+raw,p,'bg',True,*(sc['logo']or(None,None)))+' '*(inner-off-len(raw)))if i<nl else' '*inner
        o.append(R(W,p,[(1,v,'frame'),(1,' ','bg'),(inner,m,'RAW'),(1,' ','bg'),(1,v,'frame')]))
    o.append(R(W,p,[(1,v,'frame'),(1,' ','bg'),(inner-len(_vs)-1,' '*(inner-len(_vs)-1),'bg'),(len(_vs)+1,' '+_vs,'accent',True,'bg'),(1,' ','bg'),(1,v,'frame')]))
    av=tui_avail(u)
    ORD=['s','n','p','u','c','f','k','d','b','l','m','M','z','v','e','i','V','B','t','a','A','o','/','T','?','q']
    _cn=u.cur()or{};_ckd=_cn.get('kind')
    _CM={c.split(' ',1)[0]:c for c in CMD};_CMS=[_CM[k] for k in ORD if k in _CM]
    cbar=[(_CMS[2*i]if 2*i<len(_CMS)else'',_CMS[2*i+1]if 2*i+1<len(_CMS)else'')for i in range((len(_CMS)+1)//2)]
    cw=aw//2
    def kseg(part):
        if not part or stage<3:return[(cw,' '*cw,'bg')]
        ky,nm=part.split(' ',1);ok=bool(av.get(nm))
        if ky=='z':nm='→fold'if u.hmode else'→pan'
        elif ky=='k'and _ckd in('tpl-root','tpl-raw'):nm='tpl rm'
        if not ok:return[(1,' ','bg'),(len(ky),ky,'sub'),(cw-1-len(ky),' '+nm,'sub')]
        col=fgc(p.get('accent')or'ffffff')
        if nm in CONST:pre=UND;post=UNDOFF
        else:pre=BOLD+UND;post=BOFF+UNDOFF
        return[(1,' ','bg'),(len(ky),col+pre+ky+post+FG0,'RAW'),(cw-1-len(ky),' '+nm,'sub')]
    body=max(0,H-fixed_rows(H)+_shed)
    _ml=_msg_lines(_mt,_mroom,1+min(_pay,body))if _ls0 else[]
    if _ml:body=max(0,body-(len(_ml)-1))
    pad=max(0,(body-len(cbar))//2)
    _sep=R(W,p,[(1,K['jl'],'frame'),(W-2,h*(W-2),'frame'),(1,K['jr'],'frame')])
    o.append(_sep)
    HIT.update({'body0':len(o),'body':body,'pad':pad,'aw':aw,'cw':cw,'cbar':cbar})
    _hf=max(0,getattr(u,'hoff',0))
    for j in range(body):
            jj=j-pad
            kl,kr=cbar[jj]if 0<=jj<len(cbar)else('','')
            ri=u.top+j
            tn=u.rows[ri][1] if(ri<len(u.rows))else None
            vis=(stage>=3)and(nrow is None or jj<nrow)
            t=row_txt(tn,u.rows[ri][0],ri==u.sel)if(tn is not None and vis)else''
            sel=(ri==u.sel and tn is not None and vis)
            fg=_row_fg(t,sel,(tn or{}).get('kind')if tn is not None else None)
            if _hf and t:t=_panw(t,_hf)
            shown=(stage>=3)and(nrow is None or jj<nrow)
            if shown and jj==body-1 and len(cbar)>body:
                kc=[(1,' ','bg'),(aw-2,('? help')[:aw-2],'sub'),(1,' ','bg')]
            else:
                kc=(kseg(kl)+kseg(kr))if shown else(kseg('')+kseg(''))
            t=_markrow(t,sel,bool(tn and tn.get('id')and tn['id']in u.marked))
            o.append(R(W,p,[(1,v,'frame')]+kc+[(1,v,'frame'),(1,' ','bg'),(bw,t,fg,sel,'selbg'if sel else'bg'),(1,' ','bg'),(1,v,'frame')]))
    o.append(_sep)
    n=u.cur()
    _nm='  '+('[%s] %s'%(tui_glyph(n),tui_name(n))if n else _emptytree(u))
    _dp=('  #%s'%csb.short_id(n['id']))if(n and n.get('id'))else''
    if stage>=4:
        _a0=getattr(u,'anch',None)
        _an=''if(_a0 and n and n.get('id')==_a0)else _anchorlabel(u.rows,_a0)
        _pn=('   [pan +%d]'%_hf)if _hf else''
        _wt=u.status
        Rt=(u.msg or _wt)or'';_mk2=(_mk.strip()+'  ')if(_mk and Rt)else'';Rt=_mk2+Rt
        _rw=vw(Rt)
        if not Rt:line=_sb_left(_nm,_dp,'',_an,_pn,inner)
        elif _ml:line=_ml[0]+' '*max(0,inner-_mkw-vw(_ml[0]))+_mk
        else:
            _lm=inner-_rw-3
            _ls=_sb_left(_nm,_dp,'',_an,_pn,_lm)
            line=_ls+' '*max(0,_lm-vw(_ls))+v+' '+Rt
        o.append(R(W,p,[(1,v,'frame'),(1,' ','bg'),(inner,line[:inner],'fg'),(1,' ','bg'),(1,v,'frame')]))
        for _x in(_ml[1:]if _ml else[]):
            o.append(R(W,p,[(1,v,'frame'),(1,' ','bg'),(inner,_x[:inner],'fg'),(1,' ','bg'),(1,v,'frame')]))
    else:
        o.append(R(W,p,[(1,v,'frame'),(1,' ','bg'),(inner,' '*inner,'bg'),(1,' ','bg'),(1,v,'frame')]))
    o.append(R(W,p,[(1,K['bl'],'frame'),(W-2,h*(W-2),'frame'),(1,K['br'],'frame')]))
    if getattr(u,'modal',None):
        m=u.modal;_mr=max(6,H-8)
        art,iw,meta=box_art(W,m.get('title')or'',m.get('body')or[],m.get('top',0),min(m.get('rows')or _mr,_mr),cols=m.get('cols'),status=m.get('status'),hint=m.get('hint')or'ESC',hlim=H)
        _m=modal_lines(W,H,art,p,meta)
        assert len(_m)==H,'modal lines %d != %d'%(len(_m),H)
        return _m
    _o=list(o)
    assert len(_o)==H,'frame lines %d != %d'%(len(_o),H)
    return _o

def cbar_rows():
    return (len(CMD)+1)//2
FR=16
def fixed_rows(H):
    return FR
INTRO_WAIT=6.0
def intro_cap():
    return max(INTRO_WAIT,2.0*_fet_secs(),_gsecs())
def intro_gate(err,rows,slow,reps,why=''):
    if err or(rows and slow)or reps>=2:return True
    return bool(isinstance(why,str)and why.startswith('fetch failed:'))
def intro_sig(rows):
    return tuple(sorted(str(n.get('id')or'')for _d,n in rows or[]))
INTRO_BAND=None
def intro_body(H):
    return max(0,H-fixed_rows(H))
def intro_full(rows,slots,landed):
    n=len(rows or[])
    sl=max(0,int(slots or 0))
    if not(landed and n):return False
    return min(n,sl)==n or n>=sl
def _ipump(term):
    if term is None:return
    try:
        if not select.select([sys.stdin.fileno()],[],[],0)[0]:return
        _b=os.read(sys.stdin.fileno(),4096)
    except Exception:return
    if _b:term.pend=getattr(term,'pend',b'')+_b
_NAVSEQ=((b'\x1b[A','UP'),(b'\x1b[B','DOWN'),(b'\x1b[5~','PGUP'),(b'\x1b[6~','PGDN'),
         (b'\x1b[H','HOME'),(b'\x1b[F','END'),(b'\x1b[1~','HOME'),(b'\x1b[4~','END'),
         (b'\x1b[D','LEFT'),(b'\x1b[C','RIGHT'),
         (b'z','z'),(b'v','v'),(b'm','m'))
def _nav_now(u,term):
    if term is None:return False
    moved=False
    while True:
        pend=getattr(term,'pend',b'')or b''
        hit=None
        for _seq,_k in _NAVSEQ:
            if pend.startswith(_seq):hit=(_seq,_k);break
        if not hit:break
        term.pend=pend[len(hit[0]):]
        _k=hit[1]
        if _k=='UP':u.sel=_step(u.rows,u.sel,-1)
        elif _k=='DOWN':u.sel=_step(u.rows,u.sel,1)
        elif _k=='PGUP':u.sel=_step(u.rows,u.sel,-5)
        elif _k=='PGDN':u.sel=_step(u.rows,u.sel,5)
        elif _k in('HOME','END'):
            u.sel,_m=tui_seek(u.rows,u.sel,_k=='END')
            if _m:u.status=_m
        elif _k in('LEFT','RIGHT'):
            _fold=(_k=='LEFT')
            if getattr(u,'hmode',False):
                u.hoff=max(0,u.hoff+(-4 if _fold else 4))
            else:
                _ok,_pj,_chg=tui_fold_one(u.folded,u.rows,u.sel,_fold,u.pin)
                if _ok:
                    if _pj is not None:
                        _ns=_selok(u.rows,_pj)
                        if _ns is not None:u.sel=_ns
                    u.refold_or_fetch()
        elif _k=='z':
            u.hmode=not getattr(u,'hmode',False)
        elif _k=='v':
            _n=u.cur();_rt=(_n or{}).get('_rt')
            _did,_now,_cnt=tui_fold_root(u.folded,u.rows,_rt,u.groups,u.pin)
            if _did:u.refold_or_fetch()
        elif _k=='m':
            _n=u.cur()
            try:
                if u.on(_n).get('mark'):
                    u.marked,u.anch,u.atyp,_mm,_ok=tui_mark_toggle(u.marked,u.anch,u.atyp,_n)
                    if _ok:u.status=_mm
                    else:u.msg=_mm
            except Exception:pass
        moved=True
    if moved:
        _bd=max(1,getattr(u,'body',3))
        if u.sel<u.top:u.top=u.sel
        elif u.sel>=u.top+_bd:u.top=min(max(0,len(u.rows)-_bd),u.sel-_bd//2)
    return moved
def intro(u,W,H,draw,cut=False):
    _T=getattr(u,'_term',None)
    def put(st,nl,nr=None,nv=None):
        draw(st,nl,nr,nv)
    T0=time.time()
    _fast=[False]
    def _nonnav(pend):
        if not pend:return False
        return not any(_s.startswith(pend)or pend.startswith(_s)for _s,_k in _NAVSEQ)
    def at(dt):
        _ipump(_T)
        if _T is not None and _nonnav(getattr(_T,'pend',b'')or b''):_fast[0]=True;cut and _raise_cut(dt)
        d=T0+dt-time.time()
        if d<=0:return
        time.sleep(d)
    t=0.0
    put(1,0,None,0);t+=0.25;at(t)
    for i in range(9):
        put(2,i+1,None,0);t+=ANIM;at(t)
    nb=cbar_rows()
    for r in range(1,nb+1):
        put(3,9,r,0);t+=ANIM;at(t)
    put(4,9,INTRO_BAND,0);t+=ANIM;at(t)
    _slots=intro_body(H);_sig=None;_cnt=0;_land=False;_got=False;_emp=0;_cap=intro_cap()
    for _i in range(12):
        if _fast[0]:break
        _landed=None;_err=False
        try:_landed=u.fetch()
        except Exception:_err=True
        if _landed:put(4,9,INTRO_BAND,0);t+=0.15
        at(t)
        _s=intro_sig(u.rows);_has=bool(u.rows)
        _cnt=_cnt+1 if(_has and _s==_sig)else 0
        _sig=_s;_got=_got or _has
        _emp=_emp+1 if(_landed and not _has)else 0
        if _cnt>=1:_land=intro_full(u.rows,_slots,True);break
        if intro_gate(_err,_has,time.time()-T0>=_fet_secs(),_emp,getattr(u,'msg','')or''):break
        if time.time()-T0>=_cap:break
    if not _land and not _got:
        try:u.fetch()
        except Exception:pass
        put(4,9,INTRO_BAND,0);t+=0.15;at(t)
    if time.time()-T0>t:t=time.time()-T0
    for k in range(len(VERN)+1):
        t+=VER_ANIM;_ipump(_T);_nav_now(u,_T);put(5,9,INTRO_BAND,k);at(t)
    u.last_fetch=time.monotonic()

def term_size():
    try:x=os.get_terminal_size();return x.columns,x.lines
    except Exception:return 100,28
_TBL=str.maketrans({'↑':'^','↓':'v','←':'<','→':'>','·':'.','★':'*'})if _ASC else None
_ELT='...'if _ASC else'…'
def _astr(x):return x.translate(_TBL)if _TBL else x
_CSIMAP={b'A':'UP',b'B':'DOWN',b'C':'RIGHT',b'D':'LEFT',b'H':'HOME',b'F':'END',
         b'5~':'PGUP',b'6~':'PGDN',b'1~':'HOME',b'4~':'END',b'7~':'HOME',b'8~':'END',b'15~':'F5'}
def _esc_key(t,ch):
    t.pend=ch+getattr(t,'pend',b'')
    k=t.key()
    if k==b'WUP'or k==b'WDOWN':return k.decode()
    if k==b'PASTE':return'PASTE'
    if k.startswith(b'CLICK:'):return k.decode()
    if k==b'MOUSE':return''
    if k==b'\x1b':return'ESC'
    if k[:2]not in(b'\x1b[',b'\x1bO'):return''
    seq=k[2:]
    return _CSIMAP.get(seq[:1])or _CSIMAP.get(seq)or''
def _paste_read(t,buf):
    end=buf.find(b'\x1b[201~')
    for _ in range(400):
        if end>=0:break
        try:
            r,_,_=select.select([t.fd],[],[],0.05)
            x=os.read(t.fd,256)if r else b''
        except Exception:x=b''
        if not x:break
        buf+=x;end=buf.find(b'\x1b[201~')
    head=buf[:end]if end>=0 else buf
    rest=buf[end+6:]if end>=0 else b''
    for _nl in(b'\r\n',b'\r',b'\n'):head=head.replace(_nl,b' ')
    return head.decode('utf-8','replace')[:4096],rest
class Term:
    def __init__(s,fd):s.fd=fd;s.old=termios.tcgetattr(fd);s.raw=False;s.eof=False;s.w=sys.stdout
    def modal(s):
        if s.raw:termios.tcsetattr(s.fd,termios.TCSADRAIN,s.old);s.raw=False
    def back(s):
        if not s.raw:tty.setraw(s.fd,termios.TCSANOW);s.raw=True;s.w.write('\x1b[?25l')
    def read1(s):
        if getattr(s,'pend',b''):
            c=s.pend[:1];s.pend=s.pend[1:];return c
        try:
            c=os.read(s.fd,1)
            if not c:s.eof=True
            return c
        except Exception:s.eof=True;return b''
    def readu(s,lead):
        if not lead:return lead
        n=2 if lead[0]<0xE0 else(3 if lead[0]<0xF0 else 4)
        b=lead
        while len(b)<n:
            c=s.read1()
            if not c:break
            if not 0x80<=c[0]<0xC0:s.pend=c+getattr(s,'pend',b'');break
            b+=c
        return b
    def key(s,wait=0.06):
        if wait==0.06:
            try:wait=max(0.0,csb._sw('tui_esc_wait'))
            except Exception:wait=0.25
        c=s.read1()
        if c!=b'\x1b':return s.readu(c) if c and c[0]>=0x80 else c
        buf=getattr(s,'pend',b'')
        if not buf:
            try:
                r,_,_=select.select([s.fd],[],[],wait)
                buf=os.read(s.fd,32)if r else b''
            except Exception:buf=b''
        if not buf:return b'\x1b'
        def _more():
            try:
                r,_,_=select.select([s.fd],[],[],wait)
                return os.read(s.fd,64)if r else b''
            except Exception:return b''
        if b'[200~'.startswith(buf):
            for _ in range(8):
                _x=_more()
                if not _x:break
                buf+=_x
                if len(buf)>=5:break
            if buf[:5]!=b'[200~':
                return b''
        if buf[:5]==b'[200~':
            s.paste,rest=_paste_read(s,buf[5:]);s.pend=rest
            return b'PASTE'
        if buf[:2]==b'[<':
            for _ in range(4):
                e=max(buf.find(b'M'),buf.find(b'm'))
                if e>=0:break
                _x=_more()
                if not _x:break
                buf+=_x
            e=max(buf.find(b'M'),buf.find(b'm'))
            if e<0:return b'MOUSE'
            s.pend=buf[e+1:]
            _p=buf[2:e].split(b';')
            _b=_p[0]if _p else b''
            if _b in(b'64',b'65'):return _b==b'64'and b'WUP'or b'WDOWN'
            if _b in(b'0',b'1',b'2')and buf[e:e+1]==b'M'and len(_p)>=3:
                try:return b'CLICK:%d:%d'%(int(_p[1]),int(_p[2]))
                except Exception:return b'MOUSE'
            return b'MOUSE'
        if buf[:1]==b'O':
            while len(buf)<2:
                _x=_more()
                if not _x:break
                buf+=_x
            s.pend=buf[2:];return b'\x1bO'+buf[1:2]
        if buf[:1]==b'[':
            m=None
            for _ in range(4):
                m=re.match(rb'[0-9;]*[A-Za-z~]',buf[1:])
                if m:break
                _x=_more()
                if not _x:break
                buf+=_x
            m=re.match(rb'[0-9;]*[A-Za-z~]',buf[1:])
            if m:s.pend=buf[1+m.end():];return b'\x1b['+m.group(0)
            return b''
        s.pend=buf
        return b'\x1b'
    def restore(s):
        termios.tcsetattr(s.fd,termios.TCSADRAIN,s.old);s.w.write('\x1b[?1006l\x1b[?1000l\x1b[?2004l\x1b[?25h\x1b[2J\x1b[H'+RST);s.w.flush()
def dw(s):
    return vw(s)
def _cut(s,n):
    if dw(s)<=n:return s
    _e=_ELT if n>=dw(_ELT)else(_ELT[:max(0,n)]if _ASC else _ELT)
    o=''
    for c in s:
        if dw(o)+dw(c)>n-dw(_e):break
        o+=c
    return o+_e
def pad2(s,n):
    if dw(s)>n:
        while s and dw(s)>n:s=s[:-1]
    return s+' '*max(0,n-dw(s))
BOX={'tl':'+','tr':'+','bl':'+','br':'+','h':'-','v':'|'}if _ASC else{'tl':'╭','tr':'╮','bl':'╰','br':'╯','h':'─','v':'│'}
_CEN=csb.TUI_CEN
_MARKS=(csb.TUI_CEN,csb.TUI_VAL,csb.TUI_SEC,csb.TUI_KV,csb.TUI_WARN)
_VAL=csb.TUI_VAL
_SEC=csb.TUI_SEC
_WARNK=csb.TUI_WARN
_KV=csb.TUI_KV
_PMT_RE=re.compile(r'\[y/N\] *[A-Za-z]{0,4}$|\(y/N\) *[A-Za-z]{0,4}$|type y[^:]*: *[A-Za-z]{0,4}$'
                   r'|type the alias[^:]*: *[A-Za-z]{0,4}$|to confirm: *[A-Za-z]{0,4}$'
                   r'|select \d+-\d+> *[0-9]{0,4}$|\? *\S{0,4}$|: *[^\s]{0,4}$')
def _wrapdw(t,w,ind=''):
    if dw(t)==len(t):return textwrap.wrap(t,width=w,subsequent_indent=ind,break_long_words=True,break_on_hyphens=False)
    out=[];cur='';n=0;iw=dw(ind)
    for ch in t:
        k=dw(ch)
        if cur and n+k>w:out.append(cur);cur=ind+ch;n=iw+k
        else:cur+=ch;n+=k
    if cur:out.append(cur)
    return out
def _msg_lines(t,w,cap):
    ls=_wrapdw(t,max(1,w))or['']
    if len(ls)<=cap or cap<=0:return ls
    _f=next((i+1 for i,x in enumerate(ls[:cap])if x.rstrip().endswith(('.','!','?',':',';'))),0)
    o=ls[:(_f or cap)]
    if len(o)<len(ls):o[-1]=_cut(o[-1]+' '+ls[len(o)],max(1,w))
    return o
def _wrap_body(body,title,W,cols=None):
    body=[csb._nump(x)for x in body]
    title=_san(title);body=[_san(x)for x in body]
    need=max([dw(title)]+[min(dw(x),96) for x in body]+[24])+4
    iw0=min(max(need,int(W*0.62)),W-4);iw0=max(min(iw0,W-4),min(40,W-4))
    inner=max(8,iw0-3);w0,w1=csb.TUI_HELP_W
    flat=[];fmeta=[];_cen=[]
    for _i,_x in enumerate(body):
        _c=cols[_i]if cols and _i<len(cols)else None
        if _x.startswith(_VAL):
            flat.append(_x[len(_VAL):]);fmeta.append('val');continue
        if _x.startswith(_SEC):
            flat.append(_x[len(_SEC):]);fmeta.append('sec');continue
        if _x.startswith(_WARNK):
            flat.append(_x[len(_WARNK):]);fmeta.append('warn');continue
        if _x.startswith(_SEC):
            flat.append(_x[len(_SEC):]);fmeta.append('sec');continue
        if _x.startswith(_CEN):
            flat.append(_x[len(_CEN):]);fmeta.append('egg');_cen.append(len(flat)-1);continue
        if _c and _c[2]is not None:
            tp,ky,ds=_san(_c[0]),_san(_c[1]),_san(_c[2]);pre=w0+w1
            if inner-pre<8:
                _k=ky.strip()or tp.strip();_x=(_k+' '+ds).strip()if _k else ds;_c=None
            else:
                av=max(8,inner-pre)
                for _j,p_ in enumerate(_wrapdw(ds or'',av)or['']):
                    flat.append(tp.ljust(w0)+ky.ljust(w1)+p_ if _j==0 else' '*pre+p_)
                    fmeta.append((tp,ky,p_)if _j==0 else('','',p_))
                continue
        if len(_x)>=8 and len(set(_x))==1:
            flat.append(_x[0]*inner);fmeta.append(_c);continue
        if dw(_x)<=inner:flat.append(_x);fmeta.append(_c);continue
        _mk=_KV if _KV in _x else''
        if _mk:_p0,_v0=_x.split(_KV,1);_x=_p0+_v0
        _ind=len(_x)-len(_x.lstrip())
        _sub=' '*min(_ind if _ind else 2,14)
        for _j,_w in enumerate(_wrapdw(_x,inner,_sub)):
            if _j==0 and _mk:
                _pl=min(len(_p0),len(_w));_w=_w[:_pl]+_mk+_w[_pl:]
            flat.append(_w)
            fmeta.append(_c if _j==0 else('val' if _mk else('','',None)))
    iw=min(max(iw0,max([dw(x) for x in flat]+[24])+4),W-4)
    _fi=max(8,iw-3)
    flat=[(x[0]*_fi if len(x)>=8 and len(set(x))==1 else x)for x in flat]
    for _ci in _cen:
        flat[_ci]=' '*max(0,(_fi-vw(flat[_ci]))//2)+flat[_ci]
    return flat,fmeta,iw
def box_art(W,title,body,top=0,maxrows=None,hint='ESC',cols=None,status=None,hlim=None):
    title=_san(title);body=[_san(x)for x in body]
    maxrows=maxrows or 14
    flat,fmeta,iw=_wrap_body(body,title,W,cols)
    vn=maxrows;foot=None;n=len(flat)
    mx=max(0,n-(maxrows-1))if n>maxrows else 0
    top=max(0,min(top,mx))
    _sf=max(1,iw-3);_st=[]
    if status is not None:
        _st=[status]if dw(status)<=_sf else _msg_lines(status,_sf,2)
    if len(_st)>1 and hlim is not None:
        _h=(maxrows-1 if n>maxrows else max(6,min(maxrows,n+2)))+(1 if n>maxrows else 0)+2+3
        if _h>hlim:_st=_msg_lines(status,_sf,1)
    if n>maxrows:
        vn=maxrows-1
        lo=top+1;hi=lo+vn-1
        _up,_dn=lo>1,hi<n
        _h='↓ PgDn / ↑ PgUp  more'if(_up and _dn)else('↓ PgDn  more'if _dn else'↑ PgUp')
        foot='lines %d-%d/%d   %s'%(lo,hi,n,_h)
    else:
        vn=min(maxrows,max(3,n+len(_st)))
    vis=list(flat[top:top+vn]);vm=list(fmeta[top:top+vn])
    while len(vis)<vn:vis.append('');vm.append(None)
    if foot is not None:vis.append(foot);vm.append('foot')
    _sk='stw'if(isinstance(status,str)and'Failed'in status)else'st'
    for _x in _st:vis.append(_x);vm.append(_sk)
    hint=_cut(hint,max(4,iw-7))
    hd=max(0,iw-dw(hint)-5)
    L=[BOX['tl']+BOX['h']+(' %s '%hint)+BOX['h']*hd+BOX['tr'],
       BOX['v']+' '+pad2(_cut(title,iw-3),iw-3)+BOX['v']]
    _RULE=set('─-')if not _ASC else set('-')
    def _brow(x):
        _c=_cut(x,iw-3)
        return(_c[:-1]+' ')if _c and set(_c)<=_RULE and dw(_c)>iw-5 else pad2(_c,iw-3)
    L+=[BOX['v']+' '+_brow(x)+BOX['v'] for x in vis]
    L.append(BOX['bl']+BOX['h']*(iw-2)+BOX['br'])
    L=[_astr(x)for x in L]
    return L,iw,{2+i:vm[i]for i in range(len(vm))}
BOXCH=set('+-|')if _ASC else set('╭╮╰╯─│')
def _dk(h,f=0.5):
    try:return '%02x%02x%02x'%tuple(int(int(h[i:i+2],16)*f) for i in(0,2,4))
    except Exception:return h
def _kb(p):
    ac=p.get('accent')or'ffffff';fc=p.get('fg')or'ffffff'
    if abs(_lum(ac)-_lum(fc))>=40:return ac
    wa=p.get('warn')or ac
    if abs(_lum(wa)-_lum(fc))>=40:return wa
    sh=p.get('shadow')or''
    if sh and abs(_lum(sh)-_lum(fc))>=40:return sh
    return _dk(fc,0.55)
def _lum(h):
    try:return 0.299*int(h[0:2],16)+0.587*int(h[2:4],16)+0.114*int(h[4:6],16)
    except Exception:return 0.0

def _wl(h):
    try:
        def _c(v):
            v=v/255.0
            return v/12.92 if v<=0.04045 else((v+0.055)/1.055)**2.4
        return 0.2126*_c(int(h[0:2],16))+0.7152*_c(int(h[2:4],16))+0.0722*_c(int(h[4:6],16))
    except Exception:return 0.0

def _cr(a,b):
    x,y=_wl(a),_wl(b)
    return(max(x,y)+0.05)/(min(x,y)+0.05)

MIN_CR=3.0
def _lift(p,h,floor=MIN_CR):
    try:
        bg=_bg(p)
        tgt=floor+0.03
        if _cr(h,bg)>=tgt:return h
        up=_wl(bg)<0.18
        best=h
        for i in range(1,61):
            k=1+i*0.02 if up else max(0.0,1-i*0.02)
            c='%02x%02x%02x'%tuple(max(0,min(255,int(int(h[j:j+2],16)*k)))for j in(0,2,4))
            best=c
            if _cr(c,bg)>=tgt:return c
            if not up and k<=0.0:break
        return best
    except Exception:return h
def _mframe(p):
    f=p.get('frame')or'';s=p.get('sub')or'';bg=_lum(p.get('bg')or'000000')
    if f and abs(_lum(f)-bg)>=abs(_lum(s)-bg):return f
    return p.get('accent')or f
def _mtxt(p):
    return p.get('sub')or p.get('fg')or'ffffff'
def _mhint(p):
    fr=_mframe(p);fl=_lum(fr)
    for r in('warn','accent','sub'):
        c=p.get(r)
        if c and abs(_lum(c)-fl)>=40:return c
    return p.get('sub')or fr
_QH={}
def _qhelp(p,d,h):
    k=(p['code'],d,h)
    if k not in _QH:_QH[k]=_qhelp0(p,d,h)
    return _QH[k]
def _qhelp0(p,d,h):
    _P=_PAL[d];sh=hexs(_P[_qi(h2t(h),d)]);_lm=lambda i:_lum(hexs(_P[i]))
    def ok(i):
        return _cr(hexs(_P[i]),sh)>=MIN_CR and _qfg(tuple(_P[i]),h,d)==i
    fg=p.get('fg')or'ffffff';dc=_mtxt(p)
    if p.get('hswap'):
        cols=([_dk(dc,0.75)],[p.get('fg'),p.get('warn'),p.get('shadow'),p.get('accent'),_dk(fg,0.8)],[p.get('accent')or fg])
    else:
        cols=([dc],[p.get('accent'),p.get('fg'),p.get('warn'),p.get('shadow'),_dk(fg,0.8)],
              [p.get('warn'),p.get('accent'),p.get('shadow'),p.get('fg'),_dk(fg,0.55),_dk(fg,0.35),_dk(dc,0.5)])
    rk=[]
    for cs in cols:
        r={}
        for c in cs:
            if c and _qfg(h2t(c),h,d)not in r:r[_qfg(h2t(c),h,d)]=len(r)
        for i in sorted(range(len(_P)),key=lambda i:(_d2(_P[i],h2t(cs[0])),i)):
            if i not in r:r[i]=len(r)
        rk.append(r)
    def search(gate):
        best=None
        for i0 in rk[0]:
            if not gate(i0):continue
            for i1 in rk[1]:
                if i1==i0 or not gate(i1):continue
                for i2 in rk[2]:
                    if i2 in(i0,i1)or not gate(i2):continue
                    s=(min(abs(_lm(a)-_lm(b))for a,b in((i0,i1),(i0,i2),(i1,i2))),
                       -(4*rk[0][i0]+2*rk[1][i1]+rk[2][i2]))
                    if best is None or s>best[0]:best=(s,(i0,i1,i2))
        return best and best[1]
    def widest(gate):
        ix=sorted((i for i in range(len(_P))if gate(i)),key=_lm)
        if len(ix)<3:return None
        L=[_lm(i)for i in ix];b=0;g=-1
        for j in range(1,len(ix)-1):
            v=min(L[j]-L[0],L[-1]-L[j])
            if v>g:g,b=v,j
        return ix[b],ix[-1],ix[0]
    pick3=(search(ok)if len(_P)<=32 else widest(ok))or widest(ok)or search(lambda i:True)
    if pick3 is None:return _dk(fg,0.45),_dk(fg,0.45),_dk(fg,0.45)
    i0,i1,i2=pick3
    return hexs(_P[i2]),hexs(_P[i1]),hexs(_P[i0])
def _help_cols(p):
    d=_cdepth()
    if d!=24:return _qhelp(p,d,_bg(p))
    dc=_mtxt(p)
    def pick(cs,av):
        for h in cs:
            if h and all(abs(_lum(h)-_lum(x))>=35 for x in av):return h
        return _dk(p.get('fg')or'ffffff',0.45)
    if p.get('hswap'):
        tc=p.get('accent')or p.get('fg')
        dc=_dk(dc,0.75)
        kc=pick([p.get('fg'),p.get('warn'),p.get('shadow'),p.get('accent'),_dk(p.get('fg')or'ffffff',0.8)],[dc,tc])
        return tc,kc,dc
    kc=pick([p.get('accent'),p.get('fg'),p.get('warn'),p.get('shadow'),_dk(p.get('fg')or'ffffff',0.8)],[dc])
    tc=pick([p.get('warn'),p.get('accent'),p.get('shadow'),p.get('fg'),_dk(p.get('fg')or'ffffff',0.55),
             _dk(p.get('fg')or'ffffff',0.35),_dk(dc,0.5)],[dc,kc])
    return _lift(p,tc),_lift(p,kc),_lift(p,dc)
def _mix(h,bg,f=0.4):
    try:return '%02x%02x%02x'%tuple(int(int(h[i:i+2],16)*(1-f)+int(bg[i:i+2],16)*f)for i in(0,2,4))
    except Exception:return h
def _mfoot(p):
    return _lift(p,_dk(_mtxt(p),0.72))
def lead(l):
    s=l
    if s[:1]in BOXCH:s=s[1:]
    if s[:1]==' ':s=s[1:]
    return s.startswith('> ')
def _seccol(p):
    return _lift(p,p.get('shadow')if p.get('hswap')else p.get('accent'))
def _brt(p):
    b=p.get(_BGR)or p.get('bg')or'000000';_l=_lum(b)
    _c=[p.get(k)for k in('fg','accent','warn','sub','frame','shadow','selbg')]
    _c=[x for x in _c if x]
    return max(_c,key=lambda x:abs(_lum(x)-_l))if _c else(p.get('fg')or'ffffff')
def _pbox(l,p,kind='body',meta=None):
    _mi=-1
    fr=_mframe(p);tx=_mtxt(p);ac=p.get('accent')or tx;wa=p.get('warn')or tx;hn=_mhint(p)
    if meta:
        tc,kc,dc=_help_cols(p);w0,w1=csb.TUI_HELP_W
        pre=l[:2];post=l[-1:]if len(l)>=4 else'';mid=l[2:-1]if post else l[2:]
        if meta=='foot':core=fgc(_mfoot(p))+mid+FG0
        elif meta=='val':core=fgc(p.get('fg')or tx)+mid+FG0
        elif meta=='warn':
            core=fgc(wa)+mid+FG0
        elif meta=='sec':
            _m=re.match(r'^(\S{1,8}:)(\s*)(.*)$',mid)
            if _m:core=(BOLD+fgc(ac)+_m.group(1)+_m.group(2)+BOFF+FG0)+fgc(tx)+_m.group(3)+FG0
            else:core=BOLD+fgc(ac)+mid+BOFF+FG0
        elif meta=='egg':
            core=BOLD+fgc(_brt(p))+mid+BOFF+FG0
        elif meta in('st','stw'):
            core=(BOLD+fgc(wa if meta=='stw' else ac)+mid+BOFF)+FG0
        elif meta[2]is None:core=fgc(dc)+mid+FG0
        else:
            tp,ky,ds=meta
            core=((BOLD+fgc(tc)+tp.ljust(w0)+BOFF+FG0)if tp else' '*w0)
            core+=((fgc(kc)+ky.ljust(w1)+FG0)if ky else' '*w1)
            core+=fgc(dc)+(ds or'')+FG0+' '*max(0,vw(mid)-w0-w1-dw(ds or''))
        return fgc(fr)+pre+''.join(c for c in core if c not in _MARKS)+fgc(fr)+post+BOFF+FG0
    ok=l.startswith('Done');bad=l.startswith('Failed')
    sec=bool(re.fullmatch(r'[A-Z][A-Z0-9 ·/_-]{2,}',l.strip()))if l.strip()else False
    bad=bad or bool(re.match(r'^\s*\S+ refused:|^\s*(failed|error)[: ]',l))
    kv=None
    if kind not in('title','top')and not ok and not bad:
        _of=(2 if l[1:2]==' 'else 1)if l[:1]in BOXCH else 0
        _en=len(l)-(1 if l[-1:]in BOXCH else 0)
        _mi=l.find(_KV)
        _v=p.get('fg')or tx;_kc=p.get('accent')or _v
        if _kc==_v:_kc=_mix(_v,p.get('bg')or'000000',0.4)
        if _mi>=0:kv=(_mi,_mi+1,_kc,_v)
        else:
            _c=l[_of:_en]
            _r=re.match(r'^  ([A-Za-z_][\w.=/-]{0,30})( +)(\S.*)$',_c)
            if _r and len(_r.group(1))+len(_r.group(2))>=2+csb.CKVW-2+2:
                _k=_r.group(1);_v0=2+len(_k)+len(_r.group(2))
                kv=(_of+2+len(_k),_of+_v0,_kc,_v)
    pickrow=kind=='body'and not(ok or bad or sec)and lead(l)
    def role(c2):
        i2,ch=c2
        if ch in BOXCH:return fr,False
        if kind=='title':return ac,True
        if kind=='top':return hn,False
        if pickrow:return ac,True
        if ok:return ac,True
        if bad:return wa,True
        if sec:return _seccol(p),True
        if kv:
            if i2<kv[0]:return kv[2],False
            if i2<kv[1]:return tx,False
            return kv[3],False
        return tx,False
    cur=None;out=''
    for i2,ch in enumerate(l):
        if ch in _MARKS:continue
        r,b=role((i2,ch))
        if r!=cur:
            out+=(BOLD if b else BOFF)+FG0+fgc(r or'ffffff');cur=r
        out+=ch
    return out+BOFF+FG0
def modal_lines(W,H,art,p,meta=None):
    pc=bgc(_bg(p));o=[pc+' '*W+RST for _ in range(H)]
    iw=max([vw(l) for l in art] or [0]);bx=max(0,(W-iw)//2)
    cut=max(0,len(art)-H);by=0 if cut else max(0,(H-len(art))//2)
    for i,l in enumerate(art):
        if i<cut:continue
        y=by+i-cut
        if 0<=y<H:
            k='top'if i==0 else('title'if i==1 else('bottom'if i==len(art)-1 else'body'))
            body=_pbox(l,p,kind=k,meta=(meta or{}).get(i))
            o[y]=_astr(pc+' '*bx+body+pc+' '*max(0,W-bx-vw(l))+RST)
    return o
def modal_rows():
    return max(6,term_size()[1]-8)
def modal_max_top(body,title='',cols=None):
    W=max(1,min(term_size()[0],200))
    flat,_,_=_wrap_body(list(body)or[''],title or'',W,cols)
    mr=modal_rows();return max(0,len(flat)-(mr-1 if len(flat)>mr else mr))
def _close(u):
    u.modal=None;u.mfirst=True
def modal_view(t,title,body,u,draw,rc=0,top=None,cols=None,status=None,enter_ok=False,ret_key=False):
    body=list(body)or['(no output - the command printed nothing)'];mx=[modal_max_top(body,title,cols)];step=[max(1,modal_rows()-1)]
    top=[mx[0] if top is None else max(0,min(mx[0],top))]
    def _recalc():
        mx[0]=modal_max_top(body,title,cols);step[0]=max(1,modal_rows()-1)
        if top[0]>mx[0]:top[0]=mx[0]
    def paint():
        _recalc()
        u.modal=dict(title=title,body=body,rc=rc,top=top[0],el=-1,cols=cols,status=status,
                     hint=('ESC / Enter'if enter_ok else'ESC'));draw()
    paint();_last=[None]
    while True:
        if not _wait(t,0.25):
            if _sz_changed():paint()
            continue
        if _sz_changed():paint()
        k=t.key()
        if not k or k==b'\x1b':_last[0]=b'\x1b';break
        if k==b'T':u.next_skin();paint();continue
        if enter_ok and k in(b'\r',b'\n'):_last[0]=b'\r';break
        o=top[0]
        if k in(b'\x1b[A',b'k'):top[0]=max(0,o-1)
        elif k in(b'\x1b[B',b'j'):top[0]=min(mx[0],o+1)
        elif k==b'\x1b[5~':top[0]=max(0,o-step[0])
        elif k==b'\x1b[6~':top[0]=min(mx[0],o+step[0])
        elif k in(b'\x1b[H',b'\x1b[1~',b'\x1bOH'):top[0]=0
        elif k in(b'\x1b[F',b'\x1b[4~',b'\x1bOF'):top[0]=mx[0]
        elif k==b'WUP':top[0]=max(0,o-3)
        elif k==b'WDOWN':top[0]=min(mx[0],o+3)
        else:continue
        if top[0]!=o:paint()
    _close(u);return _last[0] if ret_key else rc
def popup(t,title,body,u,draw,rc=0,cols=None):
    rc=modal_view(t,title,body,u,draw,rc=rc,cols=cols,top=0,enter_ok=True);u.status='help closed'if str(title).startswith('csb help')else'info closed'
    draw();return rc

def show_text(t,title,lines,u,draw,status='Done'):
    return modal_view(t,title,list(lines)or['(nothing to show for this node)'],u,draw,rc=0,top=0,status=status,enter_ok=True)
_ESC=re.compile(r'\x1b\[[0-9;:?<=>]*[ -/]*[@-~]|\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)|\x1b[@-Z\\-_]')
_LB=re.compile(r'[\x0a-\x0d]')
_C0=re.compile(r'[\x00-\x1f\x7f]')
def _san(s):
    return _C0.sub('',_LB.sub(' ',str(s).replace('\t',' '*4)))
def _term_line(s):
    cells={};x=0;mx=0
    for ch in s:
        if ch=='\b':x=max(0,x-1);continue
        if ch=='\t':x=(x//8+1)*8;mx=max(mx,x);continue
        if ch<' 'or ch=='\x7f':continue
        if cells.get(x)=='':cells.pop(x,None);cells.pop(x-1,None)
        else:
            _o=cells.pop(x,None)
            if _o and _ud.east_asian_width(_o)in'WF':cells.pop(x+1,None)
        cells[x]=ch
        w=2 if _ud.east_asian_width(ch)in'WF'else 1
        if w==2:cells.pop(x+1,None);cells[x+1]=''
        x+=w;mx=max(mx,x)
    return ''.join(cells.get(i,' ')for i in range(mx)).rstrip()
def _out_lines(raw):
    t=_ESC.sub('',raw.decode('utf-8','replace')).replace('\r\n','\n');o=[]
    for seg in t.split('\n'):
        q=[x for x in seg.split('\r')if x.strip()]
        o.append(_term_line(q[-1])if q else'')
    return[l for l in o if l.strip()]
_CONF=re.compile(r'^(.*?)\s*(\[y/N\]|\(y/N\)|type y[^:]*:|type the alias[^:]*:|to confirm:|select \d+-\d+>|pick \d+-\d+>)\s*(.*)$')
def _pr_split(lines):
    out=[];pend=False
    for l in lines:
        m=_CONF.match(l)
        if not m:out.append(l);continue
        _in=re.match(r'^[ \t]*',l).group(0)
        q=_in+re.sub(r'\s+',' ',(m.group(1).strip()+' '+m.group(2)).strip())
        a=(m.group(3)or'').strip()
        out.append(q)
        if a:out.append('> '+a)
        else:pend=True
    return out,pend
def _panel_tail(lines):
    lines=list(lines)
    _q=[i for i,l in enumerate(lines) if _CONF.match(l)]
    return lines[_q[-1]:]if len(_q)>=2 else lines
def _readch(t,fd,timeout=2.0):
    try:
        if not select.select([fd],[],[],timeout)[0]:return b''
        d=os.read(fd,16)
        if not d:
            try:t.eof=True
            except Exception:pass
            return None
        return d
    except OSError:
        try:t.eof=True
        except Exception:pass
        return None
def _stale(bw,now,lp,pr):
    return bool(bw)and pr!='ans'and(now-lp)>=bw
def _reap_bg(mo,p0):
    def _w():
        try:
            while os.read(mo,65536):pass
        except Exception:pass
        try:os.close(mo)
        except Exception:pass
        try:p0.wait(timeout=3600)
        except Exception:pass
    threading.Thread(target=_w,daemon=True).start()
class _Spin:
    def __init__(s,mx=300,least=2.0):s.n=0;s.p=0;s.lp=0;s.t0=time.monotonic();s.mx=mx;s.least=least
    def hit(s):s.p+=1
    def tick(s):
        s.n+=1
        if s.n<s.mx:return False
        el=time.monotonic()-s.t0;prog=(s.p!=s.lp)
        s.n=0;s.lp=s.p;s.t0=time.monotonic()
        return el<s.least and not prog

def _child(t,av,u,draw,ti,forward,hk=None,esc_stop=False):
    env=_child_env(u)
    t0=time.time();_hk=hk or'ESC = stop waiting'
    u.modal=dict(title=ti,body=['starting...'],rc=None,top=0,el=-1,pr=False,hint=_hk,status='running... 0s');u.mfirst=True;draw()
    mo=so=None
    try:
        import pty as _p,fcntl as _f,termios as _tm,struct as _st
        mo,so=_p.openpty()
        try:
            _sc=max(20,max(1,min(term_size()[0]-1,200))-7)
            _f.ioctl(so,_tm.TIOCSWINSZ,_st.pack('HHHH',40,_sc,0,0))
        except Exception:pass
        p0=subprocess.Popen([sys.executable,os.path.join(CLI,'csb.py')]+av,stdin=so,stdout=so,stderr=so,close_fds=True,env=env,start_new_session=True)
        os.close(so);so=None
    except Exception as e:
        if mo is not None:
            try:os.close(mo)
            except Exception:pass
        return None,'failed to start: %s'%e
    raw=b'';_force=False;bl=[True,time.time()];_esc=False;_skip=False;_back=False;_stopesc=False
    def _kill():
        import signal as _sg
        for _s in(_sg.SIGTERM,_sg.SIGKILL):
            try:os.killpg(os.getpgid(p0.pid),_s)
            except Exception as _e:csb._swallow('kill',_e)
            try:p0.wait(timeout=2);return
            except Exception as _e:csb._swallow('kill',_e)
    def _pmt(ol,live=True):
        if not live:return'run'
        return'ans'if _PMT_RE.search(' '.join(ol[-4:]))else'run'
    _meof=False;_gof=False;_pst=[''];_seen_ans=False
    while True:
        try:r,_,_=select.select([t.fd]+([]if _meof else[mo]),[],[],0.25)
        except Exception:r=[]
        _sz=_sz_changed()

        ol=_out_lines(raw)
        _pr=_pmt(ol,not raw.endswith((b'\n',b'\r')))
        if _pr=='ans':_seen_ans=True
        if _pr!=_pst[0]:_pst[0]=_pr;t0=time.time()
        for f in r:
            try:
                if f==mo:
                    d=os.read(mo,65536)
                    if not d:_meof=True
                    else:raw+=d
                else:
                    k=t.key(0.03 if _pr=='ans'else 0.06)
                    if getattr(t,'eof',False):_gof=True;break
                    if k==b'T':u.next_skin();_force=True;continue
                    if k and p0.poll() is None and k not in(b'MOUSE',b'WUP',b'WDOWN')and not k.startswith(b'CLICK:'):
                        if not forward:
                            if k==b'\x1b'and esc_stop:_stopesc=True;break
                            if k==b'\x1b'or k in(b'\r',b'\n'):_skip=True;break
                            continue
                        if k==b'\x1b':
                            if _pr=='ans'or _seen_ans:
                                _back=True;_esc=True
                                try:os.write(mo,b'n\r')
                                except Exception:pass
                                break
                            else:
                                _esc=True;break
                            continue
                        if k in(b'\x1b[A',b'\x1b[B',b'\x1b[5~',b'\x1b[6~'):
                            _mt=modal_max_top(_pr_split(_panel_tail(ol))[0],ti)
                            if _mt>0:
                                _o=u.modal.get('top',0);_stp=max(1,modal_rows()-1)
                                u.modal['top']=max(0,min(_mt,_o+{b'\x1b[A':-1,b'\x1b[B':1,b'\x1b[5~':-_stp,b'\x1b[6~':_stp}[k]))
                                _force=True;draw();continue
                            u.sel=_step(u.rows,u.sel,{b'\x1b[A':-1,b'\x1b[B':1,b'\x1b[5~':-5,b'\x1b[6~':5}[k]);draw();continue
                        if k.startswith(b'\x1b'):continue
                        if _pr!='ans':
                            if k in(b'\r',b'\n'):_esc=True;break
                            continue
                        if not forward:continue
                        if k==b'PASTE':k=getattr(t,'paste','')or'';t.paste=''
                        if isinstance(k,str):k=k.encode('utf-8','replace')
                        if not k:continue
                        try:os.write(mo,k)
                        except Exception:pass
                        _force=True
                        try:
                            if select.select([mo],[],[],0.06)[0]:raw+=os.read(mo,65536)
                        except Exception:pass
            except OSError:pass
        if _esc or _gof:break
        if _skip:break
        el=int(time.time()-t0)
        _b,_pd=_pr_split(_panel_tail(ol))
        _blink=_pd
        if _blink and time.time()-bl[1]>=0.25:bl[0]=not bl[0];bl[1]=time.time()
        if _pd:_b=_b+['> '+('_'if bl[0]else' ')]
        if(_force or _sz or el!=u.modal.get('el')or _pr!=u.modal.get('pr')or _pd!=u.modal.get('pd')
           or bl[0]!=u.modal.get('bl')):
            _force=False
            u.modal['el']=el;u.modal['pr']=_pr;u.modal['pd']=_pd;u.modal['bl']=bl[0]
            u.modal['body']=_b or['waiting for the server...']
            u.modal['hint']='ESC = cancel'if _pr=='ans'else _hk
            u.modal['status']=('waiting for your answer  (y=yes  n=no  Esc=go back)'if _pr=='ans'
                               else'running... %ds'%el);draw()
        if not _esc and p0.poll() is not None:
            try:
                while True:raw+=os.read(mo,65536)
            except OSError:pass
            break
        if len(raw)>262144:
            raw=raw[-131072:];_i=raw.find(b'\n')
            if _i>=0:raw=raw[_i+1:]
    if _gof:_kill()
    if _esc or _skip:_reap_bg(mo,p0)
    else:
        try:os.close(mo)
        except Exception:pass
    return(-4 if(_back or _stopesc)else-3 if _skip else-2 if _gof else-1 if _esc else(p0.returncode or 0)),raw
_RSN=('refused','failed','error','unknown','cannot','no such','not found','missing','no snapshot','nothing matched')

def _why(lines):
    _c=[(x or'').strip() for x in (lines or[])]
    _c=[x for x in _c if x and not x.startswith(('Done','Failed','Canceled','(no output'))]
    for x in _c:
        if any(_k in x.lower() for _k in _RSN):return _cut(x,72)
    _ns=[x for x in _c if not x.startswith(('then ','(','fix','hint','try','note','example','retry','see '))]
    return _cut((_ns or _c or[''])[-1],72)
def _st(rc,why=''):
    if rc==-1:return 'Stopped waiting  - the command keeps running on the server'
    if rc==-3:return 'Stopped watching - the command keeps running'
    if rc==1:
        _l=[x or''for x in(why if isinstance(why,(list,tuple))else[why])]
        return 'still running (stopped watching)' if any('stopped watching'in x for x in _l)else'Canceled  -  nothing was changed'
    if rc==-2:return 'terminal closed  - the server keeps working'
    if rc==0:return 'Done'
    _w=_why(why) if not isinstance(why,str)else why.strip()
    return 'Failed  -  %s'%_st_head(_w) if _w else 'Failed'
def _say(what,rc):
    if rc==-4:return 'cancelled (Esc) - nothing was done'
    if rc is None or rc<0:return 'still running'if rc==-3 else'cancelled'
    return '%s ok'%what if rc==0 else '%s failed - see the panel'%what
def run_op(t,argv,u,draw,tag='',seen=None):
    av=[str(a) for a in argv];ti=(tui_argv_title(av,u.rows))if not tag else('%s   %s'%(tag,tui_argv_title(av,u.rows)))
    rc,raw=_child(t,av,u,draw,ti,True)
    if rc is None:
        modal_view(t,ti,[raw],u,draw,rc=3,status='Failed  -  the command could not be started',enter_ok=True);return 3
    if rc==-4:
        u.status='cancelled'
        _close(u)
        try:draw()
        except Exception:pass
        return rc
    _ln=_pr_split(_panel_tail(_out_lines(raw)))[0]or['(no output - the command printed nothing)'];seen is not None and seen.__setitem__(slice(None),_ln)
    modal_view(t,ti,_ln,u,draw,rc=max(rc,0),top=0,status=_st(rc,_ln),enter_ok=True)
    return rc
def _snap_name_taken(u):
    _p=getattr(u,'errd',None)
    if not _p or not os.path.exists(_p):return False
    try:
        with io.open(_p,encoding='utf-8')as _f:_last=(_f.read().strip().splitlines()or[''])[-1]
    except Exception:return False
    finally:
        try:os.unlink(_p)
        except Exception:pass
    return _last=='name_taken'
def run_capture(t,argv,u,draw,title=None):
    av=[str(a) for a in argv];ti=title or(tui_argv_title(av,u.rows))
    rc,raw=_child(t,av,u,draw,ti,False,'ESC = stop waiting')
    if rc is None:
        modal_view(t,ti,[raw],u,draw,rc=3,top=0,status='Failed  -  the command could not be started',enter_ok=True);return 3
    if rc==-4:
        u.status='cancelled'
        _close(u)
        try:draw()
        except Exception:pass
        return rc
    _ln=_pr_split(_panel_tail(_out_lines(raw)))[0]or['(no output - the command printed nothing)']
    modal_view(t,ti,_ln,u,draw,rc=max(rc,0),top=0,status=_st(rc,_ln),enter_ok=True);return rc

def tui_snap_clean_plan(t,n,rows,u,draw):
    """Two-step `d` on a snapshot: confirm once, and when the tree or the platform
    still references it, confirm again and pass --force.  Returns the CLI argv, or
    None when the user backs out."""
    sid=(n or{}).get('id')
    if not sid:return None
    _sh=csb.short_id(sid)
    if not ask_yn(t,'delete snapshot %s? (irreversible)'%_sh,u,draw):return None
    _refs=[(x.get('label')or csb.short_id(x.get('id')))
           for _d,x in(rows or[])if x.get('id')and x.get('kind')in csb.TUI_SBKIND and x.get('tpl')==sid]
    _pr=0
    try:
        _ph=csb._snap_holders(sid,getattr(u,'c',None))
        _pr=(_ph[0]if _ph else 0)or 0
    except Exception:_pr=0
    if not _refs and not _pr:return['clean',sid,'--yes']
    _w=', '.join(_refs[:4])or('the platform still counts %d runtime ref(s)'%_pr)
    if not ask_yn(t,'delete %s anyway?'%_sh,u,draw,
                  body=('still referenced by: %s'%_w,
                        'they keep running; only the link goes')):return None
    return['clean',sid,'--yes','--force']

def run_bulk(t,args_list,u,draw,what='op'):
    rc=0;nn=len(args_list);lines=[];nok=0;nsk=0;_sk=[];_neg=0;_last='';_escstop=False;_stop_at=0
    for i,a in enumerate(args_list,1):
        cmd=re.sub(r'\b([0-9a-f]{32})\b',lambda m:csb.short_id(m.group(1)),' '.join(str(x)for x in a if str(x)!='--yes'))
        r,raw=_child(t,a,u,draw,'%d/%d   csb %s'%(i,nn,cmd),False,esc_stop=True)
        if r is None:r=3;raw=str(raw).encode()
        if r==-4:
            _escstop=True;_stop_at=i
            lines.append(csb.ckv('cancelled (Esc)',cmd))
            _nr=nn-i
            if _nr:lines.append(csb.ckv('','  Esc stopped the batch - %d op(s) after this one were not run'%_nr))
            break
        rc=max(rc,r or 0)
        if r<0:_neg=_neg or r
        if r==-3:
            nsk+=1;_sk.append(cmd);lines.append(csb.ckv('still running',cmd))
            lines.append(csb.ckv('','  stopped watching - still running on the server'))
            continue
        _ls=_out_lines(raw);_r=_why(_ls)
        lines.append(csb.ckv('ok'if not r else('cancelled'if r<0 else'failed'),cmd))
        if r:
            _rz=_r or('the panel stopped watching - the server keeps working'if r<0
                      else'the command printed no reason - run it alone to see the full log')
            _wz=getattr(csb,'_wrapw',None)
            _rw=max(20,term_size()[0]-19)
            for _lz in ((_wz(_rz,_rw)or[_rz])if _wz else[_rz]):
                lines.append(csb.ckv('','  '+_lz))
            if r<0 and i<nn:lines.append(csb.ckv('','  the remaining %d op(s) were not run'%(nn-i)))
            if r==-2:break
        else:nok+=1
        if r and _r:_last=_r
    _w=what if nn==1 else{'sandbox':'sandboxes','snapshot':'snapshots','node':'nodes'}.get(what,what+'s')
    if _escstop:
        _sm='%d ok, %d not run (Esc)'%(nok,nn-nok)
        _stt='Canceled  -  Esc stopped the batch (%d/%d done)'%(nok,nn)
    else:
        if rc==0 and(nsk or _neg):rc=_neg if _neg else-3
        _sm='%d ok, %d failed'%(nok,nn-nok-nsk)+(', %d still running'%nsk if nsk else'')
        _stt=_st(rc)
    u.status='bulk %s: %s'%(_w,_sm)
    if _sk:
        lines.append(csb.ckv('still running',', '.join(_sk[:4]+(['+%d more'%(len(_sk)-4)]if len(_sk)>4 else[]))
                             +' - stopped waiting'))
    modal_view(t,'bulk: %d %s  -  %s'%(nn,_w,_sm),lines,u,draw,rc=rc,top=0,
               status=_stt,enter_ok=True)
    return -4 if _escstop else rc
def _yn_chk(v):
    return (True,'')if v.lower() in('y','n','yes','no','')else(False,'type y or n (Enter = no)')
def ask_yn(t,prompt,u=None,draw=None,**kw):
    r=ask(t,'%s [y/N] '%prompt,u,draw,chk=_yn_chk,**kw)
    return (r or'').strip().lower()in('y','yes')
def ask(t,prompt,u=None,draw=None,hint='',chk=None,rules=None,allow=None,body=(),title='input',ws=None):
    if not(u and draw):
        t.modal();sys.stdout.write('\x1b[2J\x1b[H'+prompt);sys.stdout.flush();buf=b''
        while True:
            ch=t.read1()
            if not ch or ch in(b'\r',b'\n'):break
            if ch==b'\x1b':buf=b'';break
            if ch==b'\x7f':
                if buf:buf=buf[:-1]
                continue
            buf+=ch
        t.back();return None if getattr(ask,'_esc',False) else buf.decode('utf-8','ignore').strip()
    buf='';bl=[True,time.time()];tp=[None];mx=[0];ask._esc=False
    def rd(follow=False):
        _ex=lambda v:[y for x in(([v]if isinstance(v,str)else list(v))) for y in str(x).split('\n')]
        b=_ex(body)+(['']if body else[])+_ex([prompt])
        if rules:b+=_ex(rules)
        b+=[('> '+buf)if buf else('> _'if bl[0]else'>  ')]
        if hint:b+=_ex(hint)
        _mx=modal_max_top(b,title);mx[0]=_mx
        tp[0]=(_mx if _mx else 0)if tp[0]is None or follow else max(0,min(_mx,tp[0]))
        _ti=title+('   (input line is at the bottom; PgUp / wheel reads the notes above)'if _mx else '')
        u.modal=dict(title=_ti,body=b,rc=None,top=tp[0],el=-1);draw()
    rd()
    while True:
        _fd=getattr(t,'fd',None)
        if _fd is not None and not getattr(t,'pend',b'')and not select.select([_fd],[],[],0.25)[0]:
            _sc=_sz_changed()
            if time.time()-bl[1]>=0.25:bl[0]=not bl[0];bl[1]=time.time();rd()
            elif _sc:rd()
            continue
        ch=t.key()
        if not ch:
            if getattr(t,'eof',False):ask._esc=True;break
            continue
        if ch in(b'WUP',b'WDOWN'):
            tp[0]=max(0,min(mx[0],(tp[0]if tp[0]is not None else mx[0])+(-3 if ch==b'WUP'else 3)));rd();continue
        if ch in(b'\x1b[5~',b'\x1b[6~'):
            _pg=max(1,modal_rows()-1)
            tp[0]=max(0,min(mx[0],(tp[0]if tp[0]is not None else mx[0])+(-_pg if ch==b'\x1b[5~'else _pg)));rd();continue
        if ch==b'MOUSE'or ch.startswith(b'CLICK:')or(ch.startswith(b'\x1b')and ch!=b'\x1b'):continue
        if ch in(b'\r',b'\n'):
            ask._ts=None
            if chk:
                _ok,_em=chk(buf.strip())
                if not _ok:
                    buf='';ask._ts=None;hint=_em;bl[0]=True;bl[1]=time.time();rd(follow=True);continue
            break
        if ch==b'\x1b':buf='';ask._esc=True;u.status='cancelled (Esc)';break
        if ch==b'\t':
            if ws:
                buf,st,cd=_tabcomplete(buf,ws,getattr(ask,'_ts',None))
                ask._ts=st
                if len(cd)>1:hint='candidates: '+'  '.join(cd[:6])+('  +%d more'%(len(cd)-6)if len(cd)>6 else'')
                rd(follow=True)
            continue
        if ch==b'PASTE':
            _p=getattr(t,'paste','')
            if allow:_p=''.join(_c for _c in _p if(allow(_c)if callable(allow)else _c in allow))
            buf+=_p;rd(follow=True);continue
        if ch in(b'\x7f',b'\x08'):
            if buf:buf=buf[:-1];rd(follow=True)
            continue
        try:c=ch.decode('utf-8')
        except Exception:continue
        if not c.isprintable():continue
        if allow and not(allow(c) if callable(allow) else c in allow):
            hint=('rejected: %r is not allowed here (letters / digits / _ / - in any language)'%c
                  if callable(allow)else'rejected: %r not allowed (allowed: %s)'%(c,allow));rd();continue
        buf+=c;rd(follow=True)
    _close(u)
    return None if ask._esc else buf.strip()

def pick_hit(title,body,maxrows,cx,cy):
    try:W,H=term_size()
    except Exception:return None
    body=list(body or[])
    art,iw,_m=box_art(W,title,body,0,maxrows,hlim=H)
    cut=max(0,len(art)-H);by=0 if cut else max(0,(H-len(art))//2);bx=max(0,(W-iw)//2)
    if not(bx<=cx-1<bx+iw):return None
    i=(cy-1)-by+cut
    if i<2:return None
    flat,_,_=_wrap_body(body,title,W,None)
    j=i-2
    if j>=len(flat):return None
    k=0
    for e,ent in enumerate(body):
        n=max(1,len(_wrap_body([ent],title,W,None)[0]))
        if k<=j<k+n:return e
        k+=n
    return None
def pick(t,title,rows,u,draw,foot='',win=14,sel=0,pre=None,keys=()):
    if not rows:return None,b'\x1b'
    n=len(rows);i=[min(max(0,sel),n-1)];top=[0]
    def rd():
        if i[0]<top[0]:top[0]=i[0]
        if i[0]>=top[0]+win:top[0]=i[0]-win+1
        body=[('> 'if j==i[0]else'  ')+rows[j][0]for j in range(top[0],min(n,top[0]+win))]
        if n>win:body.append('   [%d-%d / %d]'%(top[0]+1,min(n,top[0]+win),n))
        if pre:body=(list(pre)if isinstance(pre,(list,tuple))else[pre])+['']+body
        if foot:body+=['']+(list(foot)if isinstance(foot,(list,tuple))else[foot])
        u.modal=dict(title=title,body=body,rc=None,top=0,el=-1,rows=min(len(body)+1,max(6,term_size()[1]-8)));draw()
    rd()
    M={b'\x1b[A':-1,b'\x1b[B':1,b'\x1bOA':-1,b'\x1bOB':1,b'\x1bOC':0,b'\x1bOD':0,b'WUP':-1,b'WDOWN':1,b'\x1b[5~':-win,b'\x1b[6~':win,
       b'\x1b[H':-n,b'\x1b[F':n,b'\x1b[1~':-n,b'\x1b[4~':n,
       b'\x1bOH':-n,b'\x1bOF':n}
    k=b''
    while True:
        if not _wait(t,0.25):
            if _sz_changed():rd()
            continue
        if _sz_changed():rd()
        k=t.key()
        if not k:
            if getattr(t,'eof',False):k=b'\x1b';break
            continue
        if k==b'MOUSE':continue
        if k.startswith(b'CLICK:'):continue
        if k==b'T':u.next_skin();rd();continue
        if k in(b'\r',b'\n')or k==b'\x1b':break
        if k in M:i[0]=min(n-1,max(0,i[0]+M[k]));rd();continue
        if k in keys:break
        continue
    _close(u)
    return(None,b'\x1b')if k==b'\x1b'else(rows[i[0]][1],k)
def vol_last(c=None):
    try:
        d=csb.prefs(c).get('vol_last')or{}
        v=str(d.get('name')or'');p=str(d.get('path')or'')
        if v and p:return(v,p,bool(d.get('ro')))
    except Exception:pass
    return None
def vol_last_row(l):
    return('(same as last time: %s → %s, %s)'%(l[0],l[1],'ro'if l[2]else'rw'),'__LAST__')
def vol_last_save(v,p,ro,c=None):
    try:csb.save_prefs(c,vol_last={'name':v,'path':p,'ro':bool(ro)})
    except Exception:pass
def vol_pick(t,u,draw):
    rows=_vol_rows(u)
    u.volmap={r['name']:r['id']for r in rows}if rows else {}
    if rows is None:
        s2=ask(t,'volumes to mount (Enter=skip): ',u,draw,hint=csb.TUI_VOL_HINT,chk=tui_vol_chk)
        if s2 is None:return(None,None,None)
        if not s2:return('','',False)
        p0,v0,ro=csb.vol_mount_tok(s2)[:3]
        vol_last_save(v0,p0,ro)
        return(v0,p0,ro)
    items=[(r['name'],r['name'])for r in rows]+[('(new volume, type a name)','__NEW__')]
    _l=vol_last()
    if _l and any(r['name']==_l[0]for r in rows):items.append(vol_last_row(_l))
    items.append(('(do not mount a volume)',''))
    _sel=len(items)-1
    while True:
        v,k=pick(t,'mount a volume (create-time only)   (Enter=choose   Esc=back)',items,u,draw,sel=_sel,
                 foot=['permanent: no unmount, no rename;',
                       'snapshots hold no volume data'])
        if v is None:return(None,None,None)
        if v=='__LAST__':
            p0,ro=_l[1],_l[2];v=_l[0]
        else:
            if v=='__NEW__':
                v=ask(t,'new volume name: ',u,draw,title='NEW VOLUME',
                       body=['snapshots hold no volume data;',
                             'a restore revives its writers.'],
                       rules=csb.VOL_NAME_RULES)
                if v is None:continue
                if v:
                    if not _vol_ensure(t,v,u,draw,items):continue
                    _sel=next((i for i,r in enumerate(items)if r[1]==v),0)
                    continue
            if not v:return('','',False)
            p0=ask(t,'mount path inside the sandbox (Enter=/data): ',u,draw,
                   rules='e.g. /data or /work  -  the path must exist inside the sandbox')
            if p0 is None:continue
            p0=p0 or'/data'
            _ok,em=tui_vol_chk('%s:%s'%(p0,v))
            if not _ok:u.msg=em;continue
            _rd=ask(t,'read-only? (y/n, Enter=no): ',u,draw,chk=csb.vol_ro_chk)
            if _rd is None:continue
            ro=csb.vol_ro_choice(_rd)[1]
        vol_last_save(v,p0,ro)
        return(v,p0,ro)
def _net_rows():
    try:_hist=list(csb.allow_out_hist())
    except Exception:_hist=[]
    return [(x,x)for x in _hist]
def net_onoff(t,u,draw):
    rows=[('on   - internet allowed','__ON__'),
          ('off  - no network','__OFF__')]
    v,k=pick(t,'network   (Enter=choose   Esc=back)',rows,u,draw,sel=0)
    if v is None:return None
    return 'off'if v=='__OFF__'else'on'
def net_allow(t,u,draw,tpl=None):
    _tpl_pol=csb.tpl_net_policy(csb.cfg(),(tpl or{}).get('id')or'')if tpl else None
    while True:
        try:_cur=csb.allow_out_cur(csb.cfg())or[]
        except Exception:_cur=[]
        _key=','.join(_cur)
        rows=_net_rows()
        if _key and not any(r[1]==_key for r in rows):rows.insert(0,('(current: %s)'%_key,_key))
        try:_cb=csb.egress_last_get(csb.cfg())
        except Exception:_cb=None
        _cbi=None
        if _cb:
            rows.insert(0,('(review last egress profile)','__EGRESS__'));_cbi=0
        _ti=None
        if _tpl_pol:
            rows.append(('(use template network policy)','__TPL__'));_ti=len(rows)-1
        rows+=[('all - allow everything','__D__'),
               ('type a new CIDR/domain list (only these allowed)','__T__')]
        _sel=next((i for i,r in enumerate(rows)if r[1]==_key),None)
        _dsel=next((i for i,r in enumerate(rows)if r[1]=='__D__'),None)
        if _sel is None:_sel=_dsel
        if _cbi is not None:_sel=_cbi
        elif _ti is not None:_sel=_ti
        v,k=pick(t,'allow out   (Enter=choose   d=delete   Esc=back)',rows,u,draw,sel=_sel,
                 keys=(b'd',))
        if v is None:return None
        if k==b'd':
            if v in('__D__','__T__','__TPL__','__EGRESS__'):
                u.msg='allow out: only remembered lists can be deleted';continue
            csb.save_prefs(csb.cfg(),allow_out_hist=[x for x in csb.allow_out_hist()if x!=v])
            if csb.ao_split(v)==_cur:csb.save_prefs(csb.cfg(),allow_out=[])
            u.msg='allow out: deleted %s'%v
            continue
        if v=='__EGRESS__':
            _lines=csb.egress_last_lines(csb.egress_last_get(csb.cfg())or{})
            if modal_view(t,'egress profile',_lines,u,draw,top=0,
                          status='Enter = use this profile   Esc = back',enter_ok=True,ret_key=True)in(b'\r',b'\n'):
                return'__EGRESS__'
            continue
        if v=='__TPL__':
            _lines=csb.tpl_net_lines(_tpl_pol)
            if modal_view(t,'template network policy',_lines,u,draw,top=0,
                          status='Enter = use the template policy   Esc = back',enter_ok=True,ret_key=True)in(b'\r',b'\n'):
                return'__TPL__'
            continue
        if v=='__T__':
            ao_start_typed(t,u,draw)
            continue
        if v=='__D__':
            csb.allow_out_set(csb.cfg(),[]);u.msg='allow out: all (remembered)';return []
        _vals=csb.ao_split(v)
        csb.allow_out_set(csb.cfg(),_vals);u.msg='allow out: %s (only these allowed)'%v
        return _vals
def proxy_pick_sel(rows,raw,cur):
    if cur:
        for i,r in enumerate(rows):
            if r[1]==cur:return i
    if raw=='':return len(rows)-1
    return len(rows)-1

def net_proxy(t,u,draw):
    while True:
        try:_mem=csb.prefs().get('proxy_url')
        except Exception:_mem=None
        _mem_s='' if _mem is None else str(_mem).strip()
        try:_eff=(csb._proxy_url({})or'').strip()
        except Exception:_eff=''
        rows=[(x,x)for x in csb.proxy_hist()]
        if _mem_s and not any(r[1]==_mem_s for r in rows):rows.insert(0,('(current: %s)'%_mem_s,_mem_s))
        if _eff and _eff!=_mem_s and not any(r[1]==_eff for r in rows):rows.append(('(from the environment: %s)'%_eff,_eff))
        rows+=[('type a new proxy URL','__T__'),('none - no proxy env','__N__')]
        _sel=proxy_pick_sel(rows,_mem,_mem_s)
        v,k=pick(t,'proxy   (Enter=choose   d=delete   Esc=back)   now: %s'%(_eff or'none'),rows,u,draw,sel=_sel,
                 keys=(b'd',),foot=['up = proxies used before;  none = no proxy env'])
        if v is None:return None
        if k==b'd':
            if v in('__T__','__N__'):
                u.msg='proxy: only remembered URLs can be deleted';continue
            csb.proxy_hist_del(csb.cfg(),v)
            u.msg='proxy: deleted %s'%v
            continue
        if v=='__N__':
            csb.proxy_set(csb.cfg(),'');u.msg='proxy: none (remembered)';return''
        if v=='__T__':
            _s=ask(t,'proxy URL (empty = none): ',u,draw,title='PROXY',
                   body=['example   http://<proxy-host>:<port>',
                         'injected per command by csb exec / csb shell'])
            if _s is None:continue
            _s=csb.proxy_set(csb.cfg(),_s)
            u.msg='proxy: %s'%(_s or'none')
            continue
        csb.proxy_set(csb.cfg(),v);u.msg='proxy: %s (remembered)'%v
        return v
def ao_start_typed(t,u,draw):
    _err=''
    while True:
        _body=['example   10.0.0.0/8   192.168.0.0/16   example.com',
               'the box starts empty - type the whole group',
               'separators: %s; one group = all of them'%csb.AO_SEP_UI]
        if _err:_body=[_err,'']+_body
        _s=ask(t,'allow out CIDR/domain list   (see separators below): ',u,draw,title='ALLOW OUT',body=_body)
        if _s is None:return None
        vals,prob=csb.ao_check(_s)
        if prob:
            _err='allow out: %s - empty entry (separators: , ; | or a space)'%('; '.join(prob))
            u.status=_err;continue
        if not vals:
            csb.allow_out_set(csb.cfg(),[]);u.msg='allow out: default - platform default (remembered)';return []
        bad=csb.ao_shape(vals)
        if bad:
            _err='allow out: %s - not a CIDR/domain, nothing was saved (e.g. 10.0.0.0/8 or example.com)'%', '.join(bad)
            u.status=_err;continue
        csb.allow_out_set(csb.cfg(),vals)
        u.msg='allow out: %s (remembered)'%','.join(vals);return vals
def vol_start(t,u,draw):
    vn,vp,ro=vol_pick(t,u,draw)
    if vn is None:return None,''
    if not vn:return '',''
    return csb.vol_mount_arg(vp,vn,ro,getattr(u,'volmap',None)or None)
def vol_panel(t,u,draw):
    for _ in range(9):
        rows=_vol_rows(u)
        if rows is None:
            u.status=_say('vol ls',run_op(t,['vol','ls'],u,draw));return
        items=[(tui_vol_label(r),r['id'])for r in rows]+[('(new volume...)','__NEW__'),('(close)','')]
        v,k=pick(t,'volumes   (Enter=info   d=delete   n=new   ?=notes   Esc=close)',items,u,draw,keys=(b'd',b'n',b'?'),
                 foot='volumes only mount when a sandbox is created - no hot-plug')
        if v is None or k==b'\x1b':return
        if k==b'?':
            show_text(t,'VOLUME NOTES',list(csb.vol_warn_lines(True)),u,draw);continue
        if k==b'd'and v and v!='__NEW__':
            _row=next((r for r in rows if r['id']==v or r['name']==v),{})or{}
            _blk=vol_del_block(_row,v)
            if _blk:
                u.msg=_blk;popup(t,'volume in use',[_blk],u,draw);continue
            if not ask_yn(t,'delete volume %s? (irreversible - the files in it go with it)'%csb.short_id(v),u,draw):
                u.status='cancelled';continue
            u.status=_say('vol rm',run_op(t,csb.argv_vol_rm(v),u,draw));continue
        if k==b'n'or v=='__NEW__':
            nm=ask(t,'new volume name: ',u,draw,title='NEW VOLUME',body=csb.vol_warn_lines(True,short=True),
                    rules=csb.VOL_NAME_RULES)
            if not nm:u.status='cancelled: no volume';continue
            u.status=_say('vol create',run_op(t,csb.argv_vol_create(nm),u,draw))
            continue
        if v:
            _vid=next((r['id']for r in rows if r['id']==v),v)
            it=tui_vol_card(v,_vid)
            show_text(t,it[0],it[1:],u,draw)
        else:return

_FRAME=[None,0.0]
def _ftick(ln,old,full,pc):
    if not full:
        _c=[(i,x)for i,x in enumerate(ln)if i>=len(old)or old[i]!=x]
        if not _c:return None
        return ''.join('\x1b[%d;1H'%(i+1)+pc+KCLR+x for i,x in _c)+RST,list(ln),False
    return ('\x1b[H'+''.join('\x1b[%d;1H'%(i+1)+pc+KCLR+x for i,x in enumerate(ln))
            +RST+'\x1b[H'),list(ln),True
def _fsame(a,b):
    return a is not None and a==b
_SZ=[0,0]
def _sig_exit(t,sig):
    try:t.restore()
    except Exception:pass
    for _s in (sys.stdout,sys.stderr):
        try:_s.flush()
        except Exception:pass
    os._exit(128+sig)
def _sz_changed():
    try:w,h=term_size()
    except Exception:return False
    if[w,h]!=_SZ:_SZ[:]=[w,h];return True
    return False
def _wait(t,sec=0.25):
    try:
        fd=getattr(t,'fd',None)
        if fd is None:return True
        if getattr(t,'pend',b''):return True
        return bool(select.select([fd],[],[],sec)[0])
    except Exception:return True
WEDGE_S=180.0
def _wedged(beat,wr,now=None):
    now=time.monotonic()if now is None else now
    if now-beat[0]<WEDGE_S:return False
    try:return not wr()
    except Exception:return False
def _guard(t,beat):
    while True:
        time.sleep(10)
        try:
            if not _wedged(beat,lambda:bool(select.select([],[sys.stdout],[],0)[1])):continue
            sys.stderr.write('csb: terminal is gone - exiting so no ghost process is left behind\n')
            try:t.restore()
            except Exception:pass
            os._exit(0)
        except Exception:pass
def _tmux_ok():
    if not os.environ.get('TMUX'):return False
    try:return subprocess.call(['tmux','list-sessions'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=5)==0
    except Exception:return False
def _shell_argv(u,op):
    env=dict(os.environ);env.update(CUBE_API_URL=u.c['api'],CUBE_API_KEY=u.c['key'],CSB_REGISTRY=u.c['reg'])
    return[os.path.join(CLI,'csb.py'),'shell',op],env
def _mux():
    if os.environ.get('TMUX')and _tmux_ok():return 'tmux'
    if os.environ.get('STY'):
        try:
            if subprocess.call(['screen','-ls'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=5)==0:return 'screen'
        except Exception:pass
    return None
def mux_hint(mux=None,tmux=None,screen=None):
    if mux:return ''
    tmux=bool(shutil.which('tmux'))if tmux is None else tmux
    screen=bool(shutil.which('screen'))if screen is None else screen
    return('start csb tui inside tmux or screen to open a new window'if tmux or screen
           else'install tmux or screen to get window shortcuts')
def _herdr_ok():
    if os.environ.get('HERDR_ENV')!='1'or not shutil.which('herdr'):return False
    try:return subprocess.call(['herdr','status'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=5)==0
    except Exception:return False
HERDR_KIND={'pi':'pi','senpi':'pi','cc':'claude','claude':'claude','omp':'omp','codex':'codex','gemini':'gemini',
            'cursor':'cursor','amp':'amp','kimi':'kimi','grok':'grok','qwen':'qwen','opencode':'opencode'}
def _herdr_kind(lab):
    return HERDR_KIND.get(re.sub(r'_\d+$','',(lab or'').strip()).lower(),'')
def _herdr_open(nm,cmd):
    base=['herdr','tab','create','--label',nm,'--cwd',os.getcwd(),'--no-focus']
    _ws=os.environ.get('HERDR_WORKSPACE_ID')
    _v=([base+['--workspace',_ws],base]if _ws else[base])
    pid=''
    for _a in _v:
        try:r=subprocess.run(_a,capture_output=True,text=True,timeout=8)
        except Exception:continue
        if r.returncode:continue
        try:pid=json.loads(r.stdout)['result']['root_pane']['pane_id']
        except Exception:pid=''
        if pid:break
    if not pid:return False
    for _ in range(2):
        try:
            if subprocess.call(['herdr','pane','run',pid,cmd],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=8)==0:return True
        except Exception:pass
        time.sleep(0.4)
    return False
def _copy_to_mux(txt):
    ch=[]
    if os.environ.get('TMUX')and shutil.which('tmux'):
        for _a in (['tmux','load-buffer','-w','-'],['tmux','load-buffer','-']):
            try:
                if subprocess.run(_a,input=txt.encode(),timeout=3,capture_output=True).returncode==0:
                    ch.append('the tmux buffer');break
            except Exception:pass
    for c in(('wl-copy',),('xclip','-selection','clipboard'),('xsel','-ib'),('pbcopy',)):
        try:
            if shutil.which(c[0])and subprocess.run(list(c),input=txt.encode(),timeout=2,
                    stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0:
                ch.append(c[0]);break
        except Exception:pass
    try:
        sys.stdout.write('\x1b]52;c;%s\x07'%base64.b64encode(txt.encode()).decode())
        sys.stdout.flush()
    except Exception:pass
    return ch
def _envp(env):
    _v=['%s=%s'%(k,shlex.quote(str(env[k])))for k in('CUBE_API_URL','CUBE_API_KEY','CSB_REGISTRY')if env.get(k)]
    return('env '+' '.join(_v)+' ')if _v else''

def _shell_cmd(op):
    return 'csb shell %s'%op
def _win_name(lab):
    s=re.sub(r'[\s:.]+','_',(lab or'').strip())[:24].strip('_')
    return s or 'csb-shell'
def _hold(inner):
    return('%s; _csb_rc=$?; if [ $_csb_rc -ne 0 ]; then echo; '
           'echo "[csb] the shell exited with $_csb_rc - read the message above, then press Enter to close"; '
           'read _csb_x; fi')%inner
def _clip_ok():
    if os.environ.get('TMUX')and shutil.which('tmux'):return True
    return any(shutil.which(c)for c in('wl-copy','xclip','xsel','pbcopy'))
def shell_modes(mux=None,herd=False,clip=True):
    m=[('copy the command  -  paste it into any terminal' if clip else
        'copy the command  -  no clipboard tool here, the command is shown instead','copy')]
    if mux=='tmux':m.append(('open a new tmux window','tmux'))
    elif mux=='screen':m.append(('open a new screen window','screen'))
    if herd:m.append(('open a new HERDR WINDOW  -  herdr tracks the agent inside','herdr'))
    m.append(('just show the command  -  copy it by hand','print'))
    return m
def shell_attach(t,op,lab,u,draw):
    mux=_mux();herd=_herdr_ok();clip=_clip_ok()
    argv,_env=_shell_argv(u,op)
    inner=' '.join(shlex.quote(x)for x in[sys.executable]+argv)
    _chs=[x for x in(mux,'herdr'if herd else'')if x]
    _foot=['inside the sandbox shell type  exit  to come back here',
           'Ctrl-C stays here; signal it: csb int %s -- <pattern>'%op]
    _mh=mux_hint(mux)
    if _mh:_foot.append(_mh)
    while True:
        v,_k=pick(t,'shell %s%s   (up to four, env decides)'%(lab,'   [%s]'%'+'.join(_chs)if _chs else''),shell_modes(mux,herd,clip),u,draw,sel=0,
                  foot=_foot)
        if not v:u.status='cancelled';return
        if v=='copy':
            _c=_shell_cmd(op);_ch=_copy_to_mux(_c)
            u.status=('copied to %s'%' + '.join(_ch)) if _ch \
                     else 'no clipboard tool here - showing the command'
            u.mfirst=True
            try:draw()
            except Exception:pass
            if not _ch:
                show_text(t,'SHELL %s'%lab,['run this in any terminal:','   %s'%_c,'',
                                            'no clipboard tool here - select the line above, or install xclip/wl-copy'],
                          u,draw,status='Done')
            return
        if v=='print':
            show_text(t,'SHELL %s'%lab,['run this in any terminal:','   %s'%_shell_cmd(op),'',
                                        'add  exit  there to come back here.'],u,draw,status='Done')
            continue
        _nm=_win_name(lab);ok=False;_k=''
        try:
            if v=='tmux':
                _r=subprocess.run(['tmux','new-window','-P','-F','#{window_id}','-n',_nm,_hold(_envp(_env)+inner)],
                                  capture_output=True,text=True,timeout=6)
                _wid=(_r.stdout or'').strip();ok=_r.returncode==0 and bool(_wid)
                if ok:subprocess.call(['tmux','set-option','-w','-t',_wid,'automatic-rename','off'])
            elif v=='screen':
                ok=subprocess.call(['screen','-X','screen','-t',_nm,'/bin/sh','-c',_hold(_envp(_env)+inner)])==0
            else:
                _k=_herdr_kind(lab)
                ok=_herdr_open(_nm,_hold(('HERDR_AGENT=%s '%_k if _k else'')+_envp(_env)+inner))
        except Exception:ok=False
        u.status=('opened %s %s'%(v,_nm)) if ok \
                 else '%s did not open a window - press i and try again'%v
        u.mfirst=True
        try:draw()
        except Exception:pass
        return

def esc_step(u):
    _nm=len(getattr(u,'marked',())or());_hf=bool(getattr(u,'flt',''))
    u.markdrop=0
    if _hf:
        u.flt=''
        if hasattr(u,'fetch'):u.fetch(0,again=True)
        u.msg='filter cleared'+(' - %d mark(s) left, Esc again'%_nm if _nm else '')
        return 'filter'
    if _nm:
        u.marked.clear();u.msg='marks cleared (%d)'%_nm
        return 'marks'
    u.msg='q quits'
    return 'quit'

def undo_status(dead):
    return csb._nump('undid %d - next start adopts them again'%len(dead)) if dead else 'nothing to undo - adopted records are kept'

def main(c=None):
    u=UI(c);globals()['u']=u;fd=sys.stdin.fileno();t=Term(fd);t.pend=b''
    tui_autohide_askable()
    _bm=os.environ.pop('CSB_DEV_BOOT_MSG',None)or os.environ.pop('CSB_DEV_BOOT_MSG',None)
    try:u.fetch();_w=(getattr(csb,'_WIPED',[None])or[None])[0];u.status=_w or u.status;u.msg=_w or _bm
    except Exception as e:_fetchfail(e);return 3
    t.back()
    for _sig in(signal.SIGTERM,signal.SIGHUP,signal.SIGQUIT):
        try:signal.signal(_sig,lambda s,f,t=t:_sig_exit(t,s))
        except Exception:pass
    t.w.write('\x1b[?1000h\x1b[?1006h\x1b[?2004h');t.w.flush()
    u._term=t
    _FRAME[0]=None;_FRAME[1]=0.0
    _beat=[time.monotonic()]
    threading.Thread(target=_guard,args=(t,_beat),daemon=True).start()
    try:
        def draw(st=4,nl=9,nr=None,nv=None):
            mf=getattr(u,'mfirst',False)
            if mf:u.mfirst=False
            W2,H2=term_size()
            if _sz_changed():_FRAME[0]=None
            _bd=max(1,max(3,H2-fixed_rows(H2)))
            u.body=max(3,H2-fixed_rows(H2))
            if u.top>max(0,len(u.rows)-_bd):u.top=max(0,len(u.rows)-_bd)
            if u.sel<u.top:u.top=u.sel
            elif u.sel>=u.top+_bd:u.top=min(max(0,len(u.rows)-_bd),u.sel-_bd//2)
            _o=view(u,u.ki,u.sc(),max(1,min(W2,200)),H2,*_intro_st(st,nl,nr,nv));_pc=bgc(_bg(u.sc()))
            _ln=[((x[:-len(RST)]+_pc+' '*max(0,W2-vw(x))+RST)if x.endswith(RST)else x)for x in _o]
            _full=(_FRAME[0] is None)or mf or csb._sw('tui_force_redraw')
            _age=time.time()-_FRAME[1]
            _rs=csb._sw('tui_full_redraw_secs')
            _hd=csb._sw('tui_resync_sec')
            if _hd and _age>=_hd:_full=True
            _stale=bool(_rs) and _age>=_rs
            if _stale and _fsame(_FRAME[0],_ln):_full=True
            if not _full and _fsame(_FRAME[0],_ln):return
            _pt=_ftick(_ln,_FRAME[0],_full,_pc)
            if _pt is None:return
            _paint,_FRAME[0]=_pt[0],_pt[1]
            if _pt[2]:_FRAME[1]=time.time()
            t.w.write(_paint);t.w.flush()
        if not csb._sw('ui_no_splash'):
            W0,H0=term_size();_iw=max(1,min(W0,150))
            if _iw>=45 and H0>=MINH:intro_cut(u,_iw,H0,draw)
            else:u.last_fetch=time.monotonic()
        u._term=None
        draw()
        _SP=_Spin()
        _sw=[time.time(),None]
        u.swp=None
        _gone=[False]
        while True:
            _beat[0]=time.monotonic();u.poll()
            if u.modal is None and tui_autohide_pending() is not None:
                try:_autohide_ask(t,u,draw)
                except Exception:
                    tui_autohide_answer(False)
            if _SP.tick():break
            W,H=term_size();W=max(76,min(W,150));u.ki='5'
            if _sw[1] is not None:
                u.swp=_sw[1]/float(SWP_FRAMES);_sw[1]+=1
                if _sw[1]>SWP_FRAMES:u.swp=None;_sw[1]=None;_sw[0]=time.time()
            elif SWP_ON and not getattr(u,'modal',None)and time.time()-_sw[0]>=SWP_SEC:
                _sw[1]=0
            bh=max(10,H-fixed_rows(H))
            u.top=max(0,min(u.top,max(0,len(u.rows)-bh)))
            if u.sel<u.top:u.top=u.sel
            if u.sel>=u.top+bh:u.top=max(0,u.sel-bh+1)
            draw()
            try:r,_,_=select.select([sys.stdin],[],[],SWP_TICK if _sw[1] is not None else 0.25)
            except OSError:_gone[0]=True;break
            if not r and not t.pend:
                if time.monotonic()-getattr(u,'last_fetch',0)>=TUI_POLL:
                    csb._SWOV['cube_stop_wait']=4
                    try:u.fetch(0)
                    except Exception as e:u.msg='retrying (server silent)'
                    finally:csb._SWOV.pop('cube_stop_wait',None)
                continue
            if t.pend:
                ch=t.pend[:1];t.pend=t.pend[1:]
            else:
                ch=_readch(t,fd)
                if ch is None:_gone[0]=True;break
                if not ch:
                    try:u.fetch(0);draw()
                    except Exception:pass
                    continue
                if len(ch)>1 and not ch.startswith(b'\x1b'):
                    t.pend=ch[1:];ch=ch[:1]
                if len(ch)==1 and ch[0]>=0x80:ch=t.readu(ch)
            if ch.startswith(b'\x1b[200~')or ch.startswith(b'[200~'):
                _off=6 if ch.startswith(b'\x1b[200~')else 5
                _p,_rest=_paste_read(t,ch[_off:]);t.pend=_rest
                u.status='pasted %d chars'%len(_p)
                try:draw()
                except Exception:pass
                continue
            _SP.hit()
            if ch.startswith(b'\x1b'):
                key=_esc_key(t,ch)
                if key.startswith('CLICK:'):
                    try:
                        _, _cx, _cy = key.split(':')
                        _hit = hit_test(u, int(_cx), int(_cy))
                    except Exception:
                        _hit = None
                    if _hit and _hit[0] == 'key':
                        key = _hit[1]
                    else:
                        if _hit and _hit[0] == 'node':
                            _ns = _selok(u.rows, _hit[1])
                            u.sel = _hit[1] if _ns is None else _ns
                        continue
            elif ch==b'\x06':key='FOLD'
            elif ch==b'\x02':key='UNFOLD'
            elif ch in(b'\x0e',b'\x10'):key='DOWN'if ch==b'\x0e'else'UP'
            else:key=ch.decode('utf-8','ignore')
            u.msg='';n=u.cur();av=tui_avail(u);op=u.arg();kd=(n or{}).get('kind')
            lab=((n or{}).get('label')or op)or''
            u.body=max(3,term_size()[1]-fixed_rows(term_size()[1]))
            _b=max(1,u.body)
            if u.sel<u.top:u.top=u.sel
            elif u.sel>=u.top+_b:u.top=min(max(0,len(u.rows)-_b),u.sel-_b//2)
            u.top=max(0,min(u.top,max(0,len(u.rows)-1)))
            if key in('WUP','WDOWN'):
                u.sel=_step(u.rows,u.sel,-3 if key=='WUP'else 3)
            if key=='UP':u.sel=_step(u.rows,u.sel,-1)
            elif key=='DOWN':u.sel=_step(u.rows,u.sel,1)
            elif key=='PGUP':u.sel=_step(u.rows,u.sel,-5)
            elif key=='PGDN':u.sel=_step(u.rows,u.sel,5)
            elif key in('HOME','END'):
                u.sel,_m=tui_seek(u.rows,u.sel,key=='END')
                if _m:u.status=_m
            elif key in('r','F5'):
                _FRAME[0]=None
                try:u.msg='refreshed'if u.fetch(0,again=True)else''
                except Exception as e:u.msg='refresh failed: %s'%e
            elif key=='ESC':
                esc_step(u)
            elif key=='PASTE':
                _p=getattr(t,'paste','')or''
                t.paste=''
                u.status='pasted %d chars'%len(_p)
                try:draw()
                except Exception:pass
                continue
            elif key in('q','Q')or key=='\x03':break
            elif key=='T':u.next_skin()
            elif key=='z':
                u.hmode=not u.hmode
                u.status='pan: arrows scroll, z folds'if u.hmode else'fold: arrows fold/unfold'
            elif key in('LEFT','RIGHT','FOLD','UNFOLD'):
                _fold=key in('LEFT','FOLD')
                if u.hmode and key in('LEFT','RIGHT'):
                    u.hoff=max(0,u.hoff+(-4 if key=='LEFT'else 4))
                    u.status='pan %d - z folds'%u.hoff
                else:
                    ok,pj,chg=tui_fold_one(u.folded,u.rows,u.sel,_fold,u.pin)
                    if not ok:u.status='nothing to fold here - this node has no children'
                    else:
                        if pj is not None:
                            _ns=_selok(u.rows,pj)
                            if _ns is not None:u.sel=_ns
                        _fv=('folded'if _fold else'unfolded')if chg else('already folded'if _fold else'already open')
                        u.status=_fv+(' + parent'if pj is not None else'')+(' (filter on)'if u.flt else'')
                        u.refold_or_fetch()
            elif key=='U':
                dead=csb.auto_adopt_undo(u.c,pending_only=True)
                csb._AUTOADOPT[:]=[]
                u.status=undo_status(dead)
                u.fetch(0,again=True)
            elif key=='v':
                rt=(n or{}).get('_rt')
                did,now,k=tui_fold_root(u.folded,u.rows,rt,u.groups,u.pin)
                if not did:u.status='nothing to fold'if rt else'v needs a template'
                else:
                    u.status=('%s all - %d template(s)'%('folded' if now else 'unfolded',k))
                    u.refold_or_fetch()
                    for _i,_r in enumerate(u.rows):
                        if _r[0]==0 and _r[1].get('_rt')==rt:
                            _ns=_selok(u.rows,_i)
                            if _ns is not None:u.sel=_ns
                            break
                    u.top=max(0,u.sel-max(0,u.body-1)//2)
            elif key=='m':
                _kids=[c for _d,c in (n.get('children')or[]) if (c or{}).get('id') and csb.markable(c)] if n and not n.get('id') else []
                if _kids:
                    _ids=[c['id'] for c in _kids]
                    _tp=tui_mtyp(_kids[0])
                    if u.marked and _tp and u.atyp and _tp!=u.atyp:
                        u.msg='type lock: marks hold %s - same type only'%u.atyp
                    elif all(i in u.marked for i in _ids):
                        for i in _ids:u.marked.discard(i)
                        u.status='unmarked %d'%len(_ids)
                    else:
                        for i in _ids:u.marked.add(i)
                        u.atyp=_tp or u.atyp;u.anch=_ids[0]
                        u.status='marked %d (Esc clears)'%len(_ids)
                elif not av.get('mark'):u.msg='marks: sandboxes/snapshots only'
                else:
                    u.marked,u.anch,u.atyp,_m,ok=tui_mark_toggle(u.marked,u.anch,u.atyp,n)
                    if ok:u.markdrop=0
                    if ok:u.status=_m
                    else:u.msg=_m
            elif key=='M':
                cid=(n or{}).get('id')if n else None
                _h=tui_range_hint(u.anch,cid)
                if _h:u.status=_h
                else:
                    u.marked,u.anch,msg=tui_range_toggle(u.rows,u.marked,u.anch,cid)
                    u.markdrop=0
                    u.status=msg
            elif key=='/':
                s2=ask(t,'filter (substring, empty=clear): ',u,draw)
                if s2 is not None:u.flt=s2
                u.refold_or_fetch()
                _before=len(getattr(u,'marked',()))
                u.marked=tui_filter_marks(getattr(u,'marked',set()),u.rows)
                _drop=_before-len(u.marked)
                u.markdrop=_drop
                u.status=('filter %r: %d hidden - unmarked (visible marks still work)'%(s2,_drop))if _drop else(('filter %r'%s2)if s2 else('filter unchanged'if s2 is None else'filter cleared'))
            elif key in('\r','\n',' '):
                if not av.get('info'):u.msg='no info for this node'
                elif kd=='tpl-root':
                    tr=[x for x in _tpl_rows(u) if x.get('id')==n['id']]
                    t0=tr[0] if tr else{}
                    it=tui_tpl_card(n,t0)
                    show_text(t,it[0],it[1:],u,draw);u.status='info closed'
                elif kd in('snap','dead','tpl-raw','stale','unknown'):
                    it=tui_info_text(n,u.c)
                    show_text(t,it[0],it[1:],u,draw);u.status='info closed'
                else:run_capture(t,['info',op],u,draw,title='SANDBOX %s'%lab)
            elif key=='?':
                _hb,_hc=help_text();popup(t,'csb help',_hb,u,draw,cols=_hc)
            elif key in('V','B')and len(getattr(u,'marked',())or())>1:
                u.status=('%s: no bulk (Esc clears the marks)'%('volume'if key=='V'else'build'))
            elif key=='V':vol_panel(t,u,draw)
            elif key=='B':
                _img=ask(t,'image reference for the new template: ',u,draw,
                         rules='<registry>/<name>:<tag>, reachable from the cluster\n  example: cube-sandbox-image.tencentcloudcr.com/demo/redis-envd:latest\n--disk/--mem/--cpu: use csb tpl build')
                if _img is None:u.status='cancelled'
                elif not _img.strip():u.status='tpl build: needs --image'
                else:
                    _al=ask(t,'template alias (becomes the family name in the tree): ',u,draw,
                            rules='lowercase letters, digits and hyphens, 1-64 chars (not tpl- / snap-)',
                            chk=tui_chk_alias)
                    if _al is None:u.status='cancelled'
                    elif not _al.strip():u.status='tpl build: needs --alias'
                    else:
                        try:u.status=_say('tpl build',run_op(t,csb.argv_tpl_build(_img.strip(),_al.strip()),u,draw))
                        except Exception as e:u.msg='bad command: %s'%e
                        try:u.fetch(0,again=True)
                        except Exception:pass
            elif key in('e','i','c','n','b','o','p','u','t','k','d','s','f','l','a','A'):
                if key in csb.TUI_BULK and not u.marked and getattr(u,'markdrop',0):
                    u.msg='%d mark(s) were hidden by the filter - nothing marked; press m on a visible node'%u.markdrop
                    continue
                if key in csb.TUI_BULK and len(u.marked)>=1 and not lab:
                    _op,_labs,_err=tui_bulk_plan(key,u.marked,u.rows)
                    u.msg=_err or'no id on this node'
                    continue
                if not lab:u.msg='no id on this node'
                else:
                    if key in csb.TUI_BULK and len(u.marked)>=1:
                        op,labs,err=tui_bulk_plan(key,u.marked,u.rows)
                        if err:u.msg=err
                        else:
                            if key=='t':
                                s3=ask(t,'timeout seconds for %d marked node(s): '%len(labs),u,draw,chk=tui_chk_timeout,
                                       rules=csb.TUI_OT_RULES)
                                aa=tui_bulk_argv(op,labs,s3) if s3 else None
                                if not aa:u.status='cancelled'
                                else:run_bulk(t,aa,u,draw,'sandbox')
                            else:
                                _nu=('node'if op=='clean'else('snapshot'if op=='snaprm'else'sandbox'))if op in('kill','pause','resume','timeout','clone','snap','snaprm','clean')else'node'
                                if len(labs)!=1:_nu={'sandbox':'sandboxes','snapshot':'snapshots','node':'nodes'}[_nu]
                                _vrb={'kill':'kill','snap':'snapshot','pause':'pause','resume':'resume','timeout':'set the timeout on','clone':'clone','snaprm':'delete','clean':'drop the local record of','adopt':'adopt'}.get(op,op)
                                _vn=sum(1 for _d,nn in u.rows if nn.get('id')in u.marked and nn.get('vols'))if op=='snap'else 0
                                if op!='snap' and (ask(t,'%s %d marked %s?%s type y: '%(_vrb,len(labs),_nu,(' %d mount a volume (not in the snapshot)'%_vn)if _vn else''),u,draw,chk=_yn_chk)or'').lower()!='y':
                                    u.status='cancelled'
                                else:
                                    aa=tui_bulk_argv(op,labs)
                                    run_bulk(t,aa,u,draw,'snapshot'if op=='snaprm'else'sandbox')
                            _mk=list(u.marked)
                            if u.status!='cancelled':u.marked.clear()
                            try:u.fetch(0,again=True)
                            except Exception:pass
                            if u.status!='cancelled'and u.rows:
                                _t=_focus(u.rows,_mk)
                                if _t is not None:u.sel=_t
                        continue
                    m=dict(e='exec',i='shell',c='clone',n='snap',b='rb',o='logs',p='pause',u='resume',t='timeout',k='kill',d='clean',s='start',f='commit',l='label-reset',a='alias',A='adopt')
                    nm=m[key]
                    if key=='e' and len(u.marked)>1:
                        _o2,_l2,_e2=tui_bulk_plan('k',u.marked,u.rows)
                        if _e2 or not _l2:u.msg=_e2 or'nothing marked'
                        else:
                            s2=ask(t,'run this on %d marked sandbox(es): '%len(_l2),u,draw,title='BULK EXEC',
                                   hint='the SAME command runs on every marked sandbox, one\n'
                                        'at a time (nothing is kept between calls)')
                            if s2:
                                if ask_yn(t,'run it on %d marked sandbox(es)?'%len(_l2),u,draw):
                                    run_bulk(t,[csb.argv_exec(L,shlex.split(s2))for L in _l2],u,draw,'sandbox')
                                else:u.status='cancelled'
                        continue
                    if len(u.marked)>1 and nm in csb.TUI_PERKEY:
                        u.status='%s: no bulk (Esc clears the marks)'%nm
                        continue
                    if not av.get(nm):u.msg=tui_why(n,nm)
                    elif key=='e':
                        s2=ask(t,'exec on %s: '%lab,u,draw,
                                hint='FRESH shell each time - send the whole command in one line.')
                        if s2:u.status=_say('exec',run_op(t,csb.argv_exec(op,shlex.split(s2)),u,draw))
                    elif key=='i':shell_attach(t,op,lab,u,draw)
                    elif key=='t':
                        s2=ask(t,'idle timeout in seconds: ',u,draw,chk=tui_chk_timeout,rules=csb.TUI_OT_RULES)
                        if s2:u.status=_say('timeout',run_op(t,csb.argv_timeout(op,s2),u,draw))
                    elif key=='u':
                        s2=ask(t,'new idle TTL in seconds (Enter = keep current): ',u,draw,chk=tui_chk_ttl,
                               rules='N replaces the idle TTL, counted from this resume\nEnter = keep the TTL it already has')
                        if s2 is None:u.status='cancelled: not resumed'
                        else:u.status=_say('resume',run_op(t,tui_resume_argv(op,s2),u,draw))
                    elif key=='A' and n.get('kind')=='unreg' and not n.get('id'):
                        u.status=_say('adopt',run_op(t,tui_adopt_argv(n),u,draw))
                    elif key=='A':
                        _tp=n.get('kind')=='tpl-raw'
                        s2=ask(t,('name this template (permanent): 'if _tp else'adopt %s as (Enter=auto <family>_NN): '%csb.short_id(n.get('id'))),u,draw,
                                chk=(tui_chk_alias if _tp else None),
                                rules=('the server stores it (PUT /templates/<id>/alias) - every ledger that points at the same server sees it' if _tp
                                       else'a LOCAL name only - the server has no metadata-update endpoint,\nso no other ledger sees it'))
                        if s2 is None:u.status='cancelled: not adopted'
                        elif _tp and not s2:u.status='cancelled - a nameless template needs a name'
                        else:u.status=_say('adopt',run_op(t,tui_adopt_argv(n,s2),u,draw))
                    elif key=='a':
                        s2=ask(t,'new alias for %s: '%(n.get('label')or n.get('id')),u,draw,chk=tui_chk_alias,
                               rules='lowercase letters, digits and hyphens, 1-64 chars (not tpl- / snap-)')
                        if s2:u.status=_say('tpl alias',run_op(t,csb.argv_alias(n['id'],s2),u,draw))
                    elif key=='n':
                        _dupH=''
                        while True:
                            s2=ask(t,'snapshot name (Enter=auto): ',u,draw,hint=_dupH,
                                   rules=_SEC+'permanent - a snapshot name cannot change later\n'
                                         +_VAL+'Enter = csb-<label>_<date>')
                            if s2 is None:u.status='cancelled: no snapshot';break
                            _sh=[];_rc=run_op(t,csb.argv_snap(op,s2),u,draw,seen=_sh)
                            if _rc==2 and _snap_name_taken(u):
                                u.status='snapshot name is taken - type another'
                                _dupH='the name "%s" is taken by a snapshot or a template - type another'%s2
                                continue
                            u.status=_say('snap',_rc);break
                    elif key=='l':
                        _fam=(n.get('family')or(n.get('label')if kd=='tpl-root'else op)or op or'')
                        s2=ask(t,'label-reset  -  family %s: first number for the next sandbox (Enter=1): '%_fam,u,draw,chk=tui_chk_cnt,
                               hint='allowed only when this family has no server sandbox and no ledger snapshot')
                        if s2 is None:u.status='cancelled'
                        elif not ask_yn(t,'reset the numbering for %s?'%_fam,u,draw):u.status='cancelled'
                        else:u.status=_say('label-reset',run_op(t,csb.argv_label_reset(_fam,s2),u,draw))
                    elif key=='s':
                        _sp=0;_nm2='';_cnt='1';_ao=None;_nmode='';_px=None;_nh0='';_dns_on=False
                        while True:
                            if _sp==0:
                                _e0=n.get('kind')=='snap'and not n.get('family')
                                _d0=tui_start_default_label(n)if _e0 else''
                                _v=ask(t,('sandbox name (Enter=%s): '%_d0)if _e0 else'sandbox name (Enter=auto <family_NN>): ',u,draw,
                                       hint=_nh0,
                                       rules='name is permanent (cannot be renamed later)   [Esc cancels]',allow=csb.lab_ok)
                                if _v is None:u.status='cancelled';break
                                _nm2=_v or _d0
                                _ne=tui_name_err(_nm2,n.get('family')or'',u.c)
                                if _ne:
                                    _nh0='rejected: %s  (1-64 letters / digits / _ / -, no spaces)'%_ne
                                    u.msg=_ne;continue
                                _nh0=''
                                _sp=1
                            elif _sp==1:
                                _v=ask(t,'how many sandboxes? (1-%d, Enter=1)   [Esc = back]: '%csb.TUI_START_MAX,u,draw,chk=tui_chk_cnt)
                                if _v is None:_sp=0;continue
                                _cnt=_v or'1'
                                _be=tui_bulk_name_err(_nm2,_cnt,n.get('family')or'',u.c)
                                if _be:u.msg=_be;continue
                                _sp=2
                            elif _sp==2:
                                _m=net_onoff(t,u,draw)
                                if _m is None:_sp=1;continue
                                _nmode=_m
                                if _m=='off':_ao=None;_dns_on=False;_sp=6
                                else:_sp=3
                            elif _sp==3:
                                _ao=net_allow(t,u,draw,tpl=n)
                                if _ao is None:_sp=2;continue
                                if _ao=='__TPL__':_nmode='inherit';_ao=None;_dns_on=False;_sp=6;continue
                                if _ao=='__EGRESS__':
                                    _c=csb.egress_last_get(csb.cfg())or{}
                                    _ao=list(_c.get('ao')or[]);_nmode='on'
                                    _dns_on=bool(_c.get('dns'))
                                    _px=str(_c.get('px')or'').strip()or None
                                    try:csb.proxy_set(csb.cfg(),str(_c.get('px')or''))
                                    except Exception:pass
                                    _sp=6;continue
                                if _ao:_dns_on=True;_sp=5
                                else:_dns_on=False;_sp=5
                            elif _sp==5:
                                _px=net_proxy(t,u,draw)
                                if _px is None:_sp=3;continue
                                _sp=6
                            else:
                                if start_volumes_come_with(n):
                                    vol='';u.status='volumes come with the snapshot'
                                    _vv=','.join(str(x)for x in(n.get('vols')or[]))
                                else:
                                    _vt,_vw=vol_start(t,u,draw)
                                    if _vt is None:_sp=5 if _nmode!='off' else 2;continue
                                    if _vw:u.msg=_vw;continue
                                    vol=_vt
                                _a,need_ask=tui_start_plan(n,lab,_nm2,_cnt,ao=_ao,mode=_nmode,no_dns=not _dns_on,px=_px)
                                if need_ask:
                                    if not ask_yn(t,'start %s sandboxes? (bulk > %d)'%(_cnt,csb.TUI_START_MAX),u,draw):
                                        u.status='cancelled';break
                                args,_=tui_start_plan(n,lab,_nm2,_cnt,vol,ao=_ao,mode=_nmode,no_dns=not _dns_on,px=_px)
                                if vol:args=args+['--yes']
                                u.status=_say('start',run_op(t,args,u,draw));break
                    elif key=='b':
                        _d0=u.rows[u.sel][0] if 0<=u.sel<len(u.rows)else 0
                        _par=None;_pd=-1
                        for _i in range(u.sel-1,-1,-1):
                            _dd,_nn=u.rows[_i]
                            if _dd<_d0:_par,_pd=_nn,_dd;break
                        if _par is None or _pd!=_d0-1 or _par.get('kind')not in csb.TUI_SBKIND:
                            u.status='orphan snapshot (no sandbox)'
                        else:
                            _pl=(_par.get('label')or csb.short_id(_par.get('id')))
                            _v,_k=pick(t,'roll back %s to this snapshot?'%_pl,
                                       [('(go back - change nothing)','no'),
                                        ('roll back  -  current state is lost, the snapshot is kept','yes')],
                                       u,draw,sel=0,
                                       pre=['sandbox   %s  (%s)'%(_pl,_par.get('state')or'-'),
                                            'snapshot  %s'%n['id'],
                                            'this puts the frozen state of that snapshot back into the sandbox.'],
                                       foot=['the sandbox keeps its id and its name; only disk and memory go back.'])
                            if _v=='yes':u.status=_say('rb',run_op(t,csb.argv_rb(_par['id'],n['id']),u,draw))
                            else:u.status='cancelled: no rollback'
                    elif key=='c':
                        s2=ask(t,'how many clones? (1-%d, Enter=1): '%csb.TUI_START_MAX,u,draw,chk=tui_chk_cnt,
                               rules='each copy gets <family>_<NN>; they share one temp snapshot, freed when the last one goes')
                        if s2 is None:u.status='cancelled: no clone'
                        else:
                            _n2=s2 or'1'
                            u.status=_say('clone',run_op(t,csb.argv_clone(op,_n2),u,draw))
                    elif key=='f':
                        s2=ask(t,'template alias (Enter=auto <family>-commit-<date>): ',u,draw,
                               chk=lambda x:(True,'')if not x else tui_chk_alias(x),
                               rules=csb.R_TPL)
                        if s2 is None:u.status='cancelled: no commit'
                        else:u.status=_say('commit',run_op(t,csb.argv_commit(op,s2),u,draw))
                    elif key=='k'and kd in('tpl-root','tpl-raw'):
                        _tl=n.get('label')or csb.short_id(op)
                        if ask_yn(t,'delete template %s? (its snapshots stay)'%_tl,u,draw):
                            u.status=_say('tpl rm',run_op(t,csb.argv_tpl_rm(op,yes=True),u,draw))
                        else:u.status='cancelled: template kept'
                    else:
                        if nm=='kill'and not ask_yn(t,'kill %s? (snapshots are not deleted)'%(lab or csb.short_id(op)),u,draw):u.status='cancelled'
                        elif nm=='clean'and kd=='snap':
                            _aa=tui_snap_clean_plan(t,n,u.rows,u,draw)
                            if _aa:u.status=_say('clean',run_op(t,_aa,u,draw))
                            else:u.status='cancelled: snapshot kept'
                        else:u.status=_say(nm,run_op(t,csb.argv_op(nm,op),u,draw))
                    try:u.fetch(0,again=True)
                    except Exception:pass
    finally:
        try:t.restore()
        except Exception:pass
    if _gone[0]:
        _lost_note()
        return 4
    return 0
def help_text():
    w0,w1=csb.TUI_HELP_W;body=[];cols=[]
    for r in tui_help_struct(SCH,VERN):
        if r[0]=='row':
            body.append((r[1].ljust(w0)+r[2].ljust(w1)+r[3]).rstrip());cols.append((r[1],r[2],r[3]))
        else:body.append(r[1]);cols.append(None)
    return body,cols

def _errlog():
    try:return csb.errlog()
    except Exception:pass
    rg=csb._sw('cube_registry')
    if rg:return os.path.join(os.path.dirname(rg),'tui-error.log')
    return os.path.join(os.path.dirname(csb._sw_dir()),'log','tui-error.log')
def _crash(e):
    import traceback
    p=csb.errlog_append('\n=== %s ===\n%s'%(csb._disp(csb._now()),traceback.format_exc()))or'(log unwritable)'
    return 'internal error: %s: %s (details: %s)'%(type(e).__name__,e,p)

def _lost_note():
    csb.errlog_append('\n=== %s ===\nterminal gone (stdin closed) - exit 4\n'%csb._disp(csb._now()))
def tui(c=None):
    n=0
    while True:
        try:return main(c)
        except KeyboardInterrupt:return 130
        except Exception as e:
            n+=1;msg=_crash(e)
            try:sys.stderr.write('csb: %s\n'%msg)
            except Exception:pass
            if n>=3:
                try:sys.stderr.write('csb: gave up after %d internal errors - fix the log above\n'%n)
                except Exception:pass
                return 1
            os.environ['CSB_DEV_BOOT_MSG']=msg

def tui_fkey(n):return(n.get('kind'),n.get('id')or n.get('label'))


def tui_on(n):
    _a=(n or{}).get('actions')
    return dict(_a)if _a is not None else csb.tree_actions(n)

def tui_adopt_argv(n,name=None):return csb.argv_adopt(n,name)

def tui_resume_argv(op,secs=None):return csb.argv_resume(op,secs)

def tui_why(n,key):
    k=(n or{}).get('kind');st=(n or{}).get('state')or'-';sb=k in csb.TUI_SBKIND and bool((n or{}).get('id'))
    if key in('pause','resume'):
        if k=='tpl-root':return'%s: sandbox only - s starts one from this template'%key
        if not sb and k!='unknown':return csb._gone_sb(key,n)
        if key=='resume':
            return'already running - nothing to resume'if st=='running'else'resume needs a paused sandbox (this one is %s)'%st
        return'already paused - nothing to pause'if st=='paused'else'pause needs a running sandbox (this one is %s)'%st
    if key in('exec','shell','snap','clone','commit','timeout'):
        if k=='tpl-root':return'%s: sandbox only - s starts one from this template'%key
        if not sb:return csb._gone_sb(key,n)
        if st=='paused':
            return'%s: paused - press u to resume'%key
        if st=='pausing':return'%s: still pausing - wait'%key
        return'%s: not on this sandbox (%s)'%(key,st)
    if key=='start':
        if k=='snap'and(n or{}).get('id')and st not in('-',''):
            return'start: snapshot not READY (%s) - n = fresh one'%st
        return'start: move to a [T] template first'
    if key=='label-reset':return'label-reset belongs to a [T] template node'
    if key=='alias':return'alias belongs to a template node - [T] or a nameless one'
    if key=='rb':return'roll back is per snapshot - move to a [s] snapshot'
    if key in('mark','range'):
        _k0=(n or{}).get('kind')
        if not(n or{}).get('id'):return'%s: this is a group heading, not an object'%key
        if _k0=='tpl-raw':return'%s: name it first (A), then s starts one'%key
        if _k0=='tpl-root':return'%s: not on a template (s starts one here)'%key
        return'%s: sandboxes and snapshots only (%s)'%(key,{'snap-root':'a snapshot group heading','dead':'a signpost for a sandbox that is gone','stale':'a leftover record'}.get(_k0,'not an object you can mark'))
    if key=='adopt':
        _ka=(n or{}).get('kind')
        if _ka=='snap':
            _nm=(n or{}).get('label')or(n or{}).get('id')or'<snapshot>'
            return'a snapshot cannot be adopted - csb start %s'%_nm
        if _ka in('dead','stale'):return'adopt: this sandbox is gone - csb start <snapshot>'
        if _ka in('tpl-root',):return'adopt: not this node - a nameless template is named with A'
        return'adopt: move to the sandbox node ([U] group)'
    if key=='logs':return'logs need a sandbox - this node is not one'
    if key=='clean':return'clean: nothing here (orphan snapshots / [D] / [E] only)'
    return'%s is not available on this node'%key

def tui_mtyp(n):
    k=(n or{}).get('kind');i=(n or{}).get('id')
    if not i:return None
    if k in('start','clone','from-snap','unknown','stale'):return'sb'
    if k=='snap'and csb.snap_cleanable(n):return'snap'
    return None

def tui_argv_title(av,rows):
    _m={}
    for _d,n in rows or[]:
        _i=n.get('id')
        if _i:_m[_i]='%s (%s)'%((n.get('label')or'').strip()or csb.short_id(_i),csb.short_id(_i))if(n.get('label')or'').strip()else csb.short_id(_i)
    return'csb '+' '.join(_m.get(str(a),str(a))for a in av if str(a)not in('--yes','--quiet'))

def tui_name(n):
    _x=str((n or{}).get('label')or(n or{}).get('id')or'?')
    return csb.short_id(_x)if _x==(n or{}).get('id')else _x

def tui_glyph(n):
    n=n or{}
    k=n.get('kind')
    if n.get('unadopted'):
        if n.get('unreg1'):
            return{'tpl-raw':'T','start':'S','clone':'S','from-snap':'S','unknown':'S','snap':'s'}.get(k,'U')
        return'U'
    if n.get('nolocal'):return{'tpl-raw':'T','start':'S','clone':'S','from-snap':'S','unknown':'S','snap':'s'}.get(k,'S')
    if k=='dead':return'E' if n.get('external') else'D'
    if k=='tpl-root'and n.get('deleted'):return'D'
    return{'tpl-root':'T','snap-root':'s','snap':'s','unreg':'U','stale':'X',
           'start':'S','clone':'S','from-snap':'S','unknown':'S'}.get(k,'?')

def tui_tag(n):
    _c=int((n or{}).get('clonetemp')or 0)
    return('in use by %s'%csb._pl(_c,'sandbox','sandboxes'))if _c else None

def tui_seek(rows,i,end=False):
    if not rows:return i,None
    d=rows[i][0];g=tui_glyph(rows[i][1])
    lo=i
    while lo>0 and rows[lo-1][0]>=d:lo-=1
    sib=[];x=lo
    while x<len(rows):
        dd,nn=rows[x]
        if dd<d:break
        if dd==d and not tui_hint(nn):sib.append(x)
        x+=1
    same=[k for k in sib if tui_glyph(rows[k][1])==g]
    if len(same)<=1:return i,'no other [%s] here'%g
    t=same[-1] if end else same[0]
    nd=rows[t][1]
    lb=tui_name(nd)or'-'
    return t,'%s: %s'%('end'if end else'home',lb)

def tui_hint(n):
    return bool((n or{}).get('_hint'))or(n or{}).get('kind')=='note'or bool((n or{}).get('_ctx'))

def tui_range_toggle(rows,marked,anch,cur_id):
    if anch is None:return marked,anch,'no range anchor yet: press m on the start node first'
    ix=[i for i,r in enumerate(rows)if r[1].get('id')]
    aa=[i for i in ix if rows[i][1]['id']==anch]
    cc=[i for i in ix if rows[i][1]['id']==cur_id]
    if not aa:return marked,anch,'anchor node is not visible (fold/filter?) - press m again'
    if not cc:return marked,anch,'cursor node not visible (fold/filter?)'
    a=aa[0];b=cc[0];lo,hi=(a,b)if a<=b else(b,a)
    ty=tui_mtyp(rows[a][1])or'sb'
    fl=[rows[i][1]['id']for i in range(lo,hi+1)if i!=a and tui_mtyp(rows[i][1])==ty]
    m2=set(marked)
    for x in fl:
        if x in m2:m2.discard(x)
        else:m2.add(x)
    if not fl:return m2,rows[b][1].get('id'),'nothing between them - no %s nodes in the span'%(ty or '?')
    return m2,rows[b][1].get('id'),'Esc clears'

def tui_fold_target(rows,sel):
    n=rows[sel][1] if rows and sel<len(rows) else None
    pj=None
    if n and not(n.get('children')or n.get('_ch')):
        j=sel-1
        while j>=0 and rows[j][0]>=rows[sel][0]:j-=1
        if j>=0:pj=rows[j];n=pj[1]
    return n,pj

def tui_fold_one(folded,rows,sel,fold,pin=None):
    n,pj=tui_fold_target(rows,sel)
    if not(n and(n.get('children')or n.get('_ch'))):return False,None,False
    k=tui_fkey(n)
    _was=k in folded
    (folded.add if fold else folded.discard)(k)
    if pin is not None:pin[k]=bool(fold)
    return True,(rows.index(pj) if pj else None),(_was!=bool(fold))

def tui_fold_root(folded,rows,rt,groups,pin=None):
    subs=[x[1] for x in rows if x[1].get('_rt')==rt]
    ks=[k for k in groups if any(tui_fkey(x)==k for x in subs)]
    if not ks and not rt:ks=[k for k in groups]
    if not ks:return False,False,0
    if all(k in folded for k in ks):
        folded.difference_update(ks)
        if pin is not None:
            for k in ks:pin[k]=False
        return True,False,len(ks)
    folded.update(ks)
    if pin is not None:
        for k in ks:pin[k]=True
    return True,True,len(ks)

def tui_chk_alias(t):
    if not t:return False,csb.alias_err(t)
    if csb.alias_err(t):return False,csb.alias_err(t)
    return True,''

def tui_chk_timeout(t):
    e=csb.timeout_err(t)
    return (False,e)if e else(True,'')

def tui_chk_ttl(t):
    if not t:return True,''
    if re.fullmatch(r'[0-9]+',t)and int(t)>0:return True,''
    return False,'new TTL: a whole number of seconds, 1 or more (Enter = keep current)'

def tui_chk_cnt(t):
    if not t:return True,''
    if re.fullmatch(r'\d+',t):return True,''
    return False,'count must be a number (Enter = 1)'

def tui_tpl_card(n,t0=None):
    t0=t0 or {};_hw=int((n or{}).get('hw')or 0);_nx=(n or{}).get('next')or csb.label_default((n or{}).get('label')or'?',1)
    return ['TEMPLATE ROOT  %s'%(n or{}).get('id','?'),'',
            csb.ckv('alias',(n or{}).get('label')or'-'),
            csb.ckv('status',t0.get('status')or'-'),
            csb.ckv('created',csb._disp(t0['ts'])if t0.get('ts')else'-'),
            csb.ckv('sandboxes','%d'%len((n or{}).get('children')or[])),'',
            'NAMING',
            ('  next default label %s (used 01-%02d)'%(_nx,_hw))if _hw else('  next default label %s (nothing handed out yet)'%_nx),
            ]

def vol_del_block(r,name):
    if (r or{}).get('refcount')or(r or{}).get('mounted_by'):
        return'volume %s is in use - kill the sandbox that mounts it first'%name
    return''

def tui_vol_label(r):
    _nm=r.get('name')or r.get('id')or''
    return _nm+('   [in use]'if r.get('refcount')or r.get('mounted_by')else'')

def tui_vol_card(v,vid=None):
    _r={}
    try:
        _r=next((x for x in csb.vol_rows(csb.cfg())if x.get('name')==v or x.get('id')==vid),{})or{}
    except Exception:_r={}
    _id=vid or v
    _cr=['VOLUME  %s'%v,
         'IN USE  %s'%('yes - kill the sandbox that mounts it before deleting'if _r.get('refcount')or _r.get('mounted_by')else'no')]
    if _id!=v:_cr.append('ID      %s'%_id)
    return _cr+['',
            'MOUNTS     create time only; no attach or detach later (TUI: s on a node)',
            'FREEZE     snap / clone / rb / commit work - the snapshot holds',
            '           rootfs + memory, never the data',
            'REATTACH   a new sandbox, rb and clone get the SAME live volume:',
            '           no restore, no copy, and the writers come back too',
            'READ IT    csb cp <sandbox>:/data/dir ./   (a file works too, same way)',
            'KEEP IT    the volume outlives every sandbox; the name cannot be changed',
            'DROP IT    csb kill <sandbox>   then   csb vol rm <volume>']

def tui_info_text(n,c=None):
    c=c or csb.cfg()
    k=(n or {}).get('kind') or '';sid=(n or {}).get('id') or ''
    if k=='snap':
        e=csb.led(c).get(sid) or {}
        _f,_why,_ok=csb.snap_facts(c);_r=(_f or {}).get(sid)or{}
        _sn=next(iter(csb._real_names(_r.get('names'),sid)),None)
        _og=e.get('origin')or _r.get('origin')or''
        ls=['SNAPSHOT  %s'%sid,'',
            csb.ckv('name',e.get('name')or _sn or n.get('label')or'(no name yet - press A to name it)'),
            csb.ckv('family',e.get('fam')or n.get('family')or'-'),
            csb.ckv('origin',csb.short_id(_og)if _og else'(origin unknown)'),
            csb.ckv('taken',csb._disp(e['ts'])if e.get('ts')else(csb._disp(_r['created'])if _r.get('created')else'-')),
            csb.ckv('status',_r.get('status')or'unknown'),
            csb.ckv('backend',_r.get('backend')or'unknown'),
            csb.ckv('orphan','yes' if n.get('orphan') else 'no')]
        if _f is None:
            ls+=['','  the snapshot list could not be read, so status and backend are',
                 '  unknown here - nothing is guessed; press Enter again to retry']
            _w=(_why or'').strip()
            _p='the snapshot list could not be read'
            if _w.startswith(_p):
                _w=_w[len(_p):].strip(' :,')
                if _w.startswith('(')and _w.endswith(')'):_w=_w[1:-1]
            if _w:
                if len(_w)>90:_w=_w[:87]+'...'
                ls+=['  (why: %s)'%_w]
        elif sid not in _f:ls+=['','  the server snapshot list has no entry for this id - the snapshot',
                                '  may be gone, or the list itself was cut short']
        return ls
    if k in('dead','stale'):
        e=csb.reg(c)['entries'].get(sid) or {}
        mine=[v or{} for v in csb.led(c).values() if (v or{}).get('origin')==sid]
        _ext=bool(n.get('external'))
        ls=['DELETED SANDBOX  %s%s'%(sid,'  (another ledger made it)'if _ext else'')if k=='dead'else'LEFTOVER RECORD  %s'%sid,'']
        ls+=((['  the local ledger never named this sandbox and the server no longer has it -',
               '  the node is here because a snapshot still points at it (its id was',
               '  recovered from that snapshot). press d once the snapshot is gone.','']if _ext else
              ['  local ledger only - d removes this node once its snapshots are gone',
               ''])if k=='dead'else
             ['  the SERVER does not list this sandbox and no local record',
              '  points here - the record is local; d removes this node.',''])
        for kk,v in(('sandbox_id',sid),('label',n.get('label')or e.get('label')),
                    ('state','(deleted)'if k=='dead'else'(unknown)'),
                    ('template',e.get('template_id')),('family',e.get('family')),
                    ('kind',e.get('kind')),('parent',e.get('parent')),
                    ('nseq',e.get('nseq')),('ts',csb._disp(e.get('ts'))if e.get('ts')else None)):
            if v not in(None,'')and not(kk=='sandbox_id'):ls.append(csb.ckv(kk,v))
        ls.append(csb.ckv('snapshots','%d still point here'%len(mine)if mine else'none - d removes this node'))
        for v in mine:ls.append('  %s  %s'%(' '*csb.CKVW,v.get('name')or v.get('label')or'(unnamed)'))
        return ls
    if k=='unknown' and sid:
        return ['SERVER SANDBOX  %s  (no local name)'%sid,
                '  server has it; no local name',
                csb.ckv('state',n.get('state')or'-'),
                csb.ckv('template',n.get('tpl')or'(unknown here)'),
                '  A adopt   o log   k kill']
    if k=='tpl-raw':
        return ['TEMPLATE  %s  (no name)'%sid,'',
                csb.ckv('alias','none - the server never got one'),
                csb.ckv('created',csb._disp(n.get('ts'))if n.get('ts')else'-'),
                csb.ckv('state',n.get('state')or'READY'),
                csb.ckv('tree','press A to name it - then it becomes a [T] root here'),
                '',
                '  csb start needs an alias']
    return ['INFO  %s'%(sid or(n.get('label')if n else'?')),'',
            '  this node is a group heading, not an object - press Enter on a node under it'if not sid else
            '  no detail view for this node - the nodes around it each have one']

def tui_stats(sbs,tps,lg):
    return dict(T=len([t for t in tps if not str(t.get('id','')).startswith('snap-')]),S=len(sbs),s=len(lg),
        paused=len([x for x in sbs if x.get('state')=='paused']),running=len([x for x in sbs if x.get('state')=='running']))

def tui_avail(u):
    av=dict(u.on(u.cur()))
    _mk=[]
    try:_mk=[nn for _d,nn in u.rows if nn.get('id')in(getattr(u,'marked',())or())]
    except Exception:_mk=[]
    if getattr(u,'marked',())or():
        for _ky,_n2 in csb.TUI_BULKNAME.items():
            if _ky=='e'and len(u.marked)<2:continue
            try:av[_n2]=bool(av.get(_n2))or any(u.on(m).get(_n2)for m in _mk)
            except Exception:pass
        if len(u.marked)>1:
            for _k in csb.TUI_PERKEY:
                if _k!='exec':av[_k]=False
    return av

def tui_bulk_plan(key,marked,rows):
    op=csb.TUI_BULK.get(key)
    if not op:return None,[],'not a bulk key'
    mk=[nn for _d,nn in rows if nn.get('id')in marked]
    labs=[nn.get('id')or nn.get('arg')or nn.get('label')for nn in mk]
    if not labs:return op,[],'all marked nodes are hidden - clear the filter (/) or expand the fold (v)'
    hid=[i for i in marked if i not in{nn.get('id')for _d,nn in rows}]
    if hid:return op,[],'%d of %d marked are hidden - clear the filter (/) or expand the fold (v)'%(len(hid),len(marked))
    ty={tui_mtyp(nn)for nn in mk}
    if key=='d':
        _kk=[nn.get('kind')for nn in mk]
        if all(k in('snap','snap-root')for k in _kk):op='snaprm'
        elif all(k=='stale'for k in _kk):op='clean'
        else:return op,[],'not all marked are snapshots - d is for snapshots'
    if op=='snaprm'and any(nn.get('kind')not in('snap','snap-root')for nn in mk):
        return op,[],'not all marked are snapshots - d is for snapshots'
    if len(ty)>1:return op,[],'marks mix sandboxes and snapshots - unmark one'
    if ty=={'snap'}and op!='snaprm':
        _r=' (template: start a sandbox from the snapshot, then commit)'if op=='adopt'else''
        return op,[],'all marked are snapshots - only d (delete) applies'+_r
    if op=='adopt'and not all(nn.get('unadopted')for nn in mk):
        return op,[],'adopt: [U] nodes only - one marked node has a name'
    _amap={'k':'kill','n':'snap','p':'pause','u':'resume','t':'timeout','c':'clone','A':'adopt'}.get(key)
    _strict=('stale','dead','snap','snap-root','unreg','tpl-root','tpl-raw')
    _bad=next((nn for nn in mk if(_amap and nn.get('kind')in _strict
                                   and not(nn.get('actions')or csb.tree_actions(nn)).get(_amap))),None)
    if _bad is not None:
        return op,[],'%s: not on this node - %s'%(key,_bulk_no(_bad,_amap))
    return op,labs,''

def _bulk_no(n,act):
    k=(n or{}).get('kind')or'?'
    if k=='stale':return'a leftover record - d removes it'
    if k=='dead':return'a deleted sandbox - d removes the record'
    if k=='snap':return'a snapshot - only d (delete) and b (roll back)'
    if k=='snap-root':return'a snapshot - only d (delete)'
    return'%s is not allowed on a %s node'%(act,k)

def tui_vol_chk(s,known=None):
    if not s:return True,''
    _p,_v,_r,why=csb.vol_mount_tok(s,known)
    return(False,why)if why else(True,'')

def _start_known(c):
    try:return{k:csb.enreg(v)for k,v in csb.reg(c)['entries'].items()}
    except Exception:return{}
def _name_taken(lab,fam,known):
    return any((not fam or e.get('family')==fam)and e.get('label')==lab for e in known.values())
def tui_name_err(nm,fam,c):
    if not nm:return''
    known=_start_known(c);e=csb.label_err(nm,fam,known)
    if _name_taken(nm,fam,known):return'name %s: already used'%nm
    if e=='bad charset/length':return'name %s: bad charset'%nm
    return ''
def tui_bulk_name_err(nm,cnt,fam,c):
    if not nm:return''
    try:k=int(cnt)
    except Exception:k=1
    known=_start_known(c)
    for lab in csb.bulk_labels(nm,k):
        e=csb.label_err(lab,fam,known)
        if _name_taken(lab,fam,known):return'name %s: already used'%lab
        if e=='bad charset/length':return'name %s: bad charset'%lab
    return ''
def tui_start_default_label(n):return csb.start_default_label(n)
def tui_start_plan(n,lab,label=None,cnt=1,vol=None,ao=None,mode=None,no_dns=False,px=None):return csb.argv_start(n,lab,label,cnt,vol,ao,mode,no_dns,px)

def tui_bulk_argv(op,labels,secs=None):return csb.argv_bulk(op,labels,secs)

def tui_help_struct(skins=None,ver=None):
    bar=('-'if csb._ASC else'─')*66
    o=[('text','TREE TUI KEYS  (csb v'+(ver or '').split('v')[-1]+')  -  help scrolls with arrows / PgUp / PgDn'),
       ('text',bar)]
    _pt=None
    for r in csb.TUI_HELP_ROWS:
        if r[0] and _pt and r[0]!=_pt:o.append(('text',''))
        _pt=r[0] or _pt
        o.append(('row',)+tuple(r))
    _fw=lambda k,v:'%-8s %s'%(k,v)
    _fi=' '*9
    o+=[('text',bar),
        ('text',csb.TUI_SEC+_fw('NODES:','[T] template  [S] sandbox  [s] snapshot  [X] leftover')),
        ('text',_fi+'[U] no local name  [D] killed sandbox  [E] killed, never named here'),
        ('text',csb.TUI_SEC+_fw('NOTES:','names are PERMANENT (only template alias can change)')),
        ('text',_fi+'volume: create time only, no detach; clone = N copies now'),
        ('text',_fi+'snap = one point you keep; rb rolls a sandbox back to one'),
        ('text',csb.TUI_SEC+_fw('SKINS:','  '.join(csb.TUI_SKINEN.get(x['code'],x['code'])for x in(skins or[])))),
        ('text',''),
        ('text',csb.TUI_CEN+csb.HELP_TAIL)]
    return o

def tui_help(skins=None,ver=None):
    w0,w1=csb.TUI_HELP_W
    return '\n'.join((x[1].ljust(w0)+x[2].ljust(w1)+x[3]).rstrip()if x[0]=='row'else x[1]
                      for x in tui_help_struct(skins,ver))+'\n'

def tui_mark_toggle(marked,anch,atyp,n):
    i=(n or{}).get('id')
    if not i:return marked,anch,atyp,'m marks nodes with an id only',False
    tp=tui_mtyp(n)
    if marked and i not in marked and atyp and tp and tp!=atyp:
        return marked,anch,atyp,'type lock: marks hold %s - same type only'%atyp,False
    marked.discard(i) if i in marked else marked.add(i)
    return marked,i,tp,'Esc clears',True

def tui_filter_marks(marked,rows):
    vis={(n or{}).get('id')for _d,n in rows}
    vis.discard(None)
    return set(marked)&vis

def tui_range_hint(anch,cid):
    if not anch:return 'no range anchor yet: press m on the start node first'
    if anch==cid:return 'anchor is this node - move to the far end, then M'
    return None

def tui_has(nd,f):
    for n in nd:
        if csb.row_match(n,f):return True
        if tui_has(n.get('children')or[],f):return True
    return False

def tui_flat(c,folded,flt='',groups=None,fold_ok=False,pin=None,tree=None):
    if tree is None:
        csb._bust()
        try:
            _sbs=csb.fetch_sbs(c);_tps=csb.tpl_rows(c);_so=csb.fetch_snap_origins(c)
            tree=csb.build_tree(_sbs,_tps,csb.reg(c),csb.led(c),_so)
        except Exception as e:return[],'fetch failed: %s'%e,fold_ok
        try:csb.seen_mark(c,_sbs,_so)
        except Exception:pass
        csb._LASTRT[0]=tree
        if getattr(csb,'_AUTOADOPT',None)and not _ADOPT_SHOWN[0]:
            _ad=csb._AUTOADOPT
            _u=globals().get('u')
            if _u is not None:
                _u.status='adopted %d (U undoes)'%len(_ad);_ADOPT_SHOWN[0]=True
        _hd=(getattr(csb,'_AHHID',[0])or[0])[0]
        if _hd:
            csb._AHHID[0]=0
            _u=globals().get('u')
            if _u is not None:
                _u.status=((_u.status+'   ')if getattr(_u,'status',None) else'')+\
                          'hid %d local record(s)'%_hd
    def sc(nd):
        for n in nd:
            ch=n.get('children')or[]
            if csb.tree_sz(ch)>csb.AUTOFOLD:folded.add(tui_fkey(n))
            sc(ch)
    sc(tree);fold_ok=True
    if pin:
        folded.difference_update([k for k,v in pin.items()if v is False])
        folded.update([k for k,v in pin.items()if v is True])
    out=[]
    if groups is not None:groups.clear()
    def go(nd,d,rt=None,pre=''):
        _ln=-1
        for _i,_x in enumerate(nd):
            if _x.get('kind')!='note':_ln=_i
        for i,n in enumerate(nd):
            ch=n.get('children')or[];last=(i==_ln)
            if ch:n.pop('_folded',None)
            n['_rt']=rt or tui_fkey(n);n['_ch']=len(ch)
            n['_hint']=n.get('kind')=='note'
            _lo,_br,_cv=('\\-- ','|-- ','|  ')if csb._ASC else ('└─ ','├─ ','│  ')
            n['_pre']=('  '+pre+('   'if n['_hint']else(_lo if last else _br)))if d>0 else'  '
            n['_cont']=(pre+('   'if last else _cv))if d>0 else''
            out.append((d,n))
            if ch:
                if groups is not None:groups.add(tui_fkey(n))
                if tui_fkey(n)in folded:
                    if not(flt and tui_has(ch,flt)):
                        n['_folded']=True
                        continue
            go(ch,d+1,n['_rt'],n['_cont'])
    go(tree,0)
    if flt:
        _k=[False]*len(out);_c=[False]*len(out);_nk=None
        for _i in range(len(out)-1,-1,-1):
            _d,_n=out[_i];_m=bool(csb.row_match(_n,flt))
            if _m or(_nk is not None and _nk>_d):_k[_i]=True;_nk=_d;_c[_i]=not _m
        _ctx=[x for x,_v in zip(_c,_k)if _v]
        out=[x for x,_v in zip(out,_k)if _v]
        for _f,(_d,_n)in zip(_ctx,out):
            if _f:_n['_ctx']=True
        _st=[]
        for _d,_n in out:
            while _st and _st[-1][0]>=_d:_st.pop()
            if _st:_st[-1][1]+=1
            _st.append([_d,0]);_n['_v']=_st[-1]
        for _d,_n in out:
            _c=_n.pop('_v',None)
            if _n.get('_ch'):_n['_chv']=_c[1]if _c else 0
    else:
        for _d,_n in out:_n.pop('_chv',None);_n.pop('_ctx',None)
    csb._dupmark([_n for _d,_n in out])
    return out,None,fold_ok

def tui_autohide_askable(on=True):
    csb._AHSK[0]=bool(on)

def tui_autohide_plan(gone,entries,can_ask=False,approved=(),asked=()):
    g=list(gone)
    rows=[((entries.get(i)or{}).get('label')or'(no name)',i)for i in g[:csb.AH_ROWS]]
    if all(i in approved for i in g):return'auto',rows
    if len(g)<csb.AUTOHIDE_MAX:return'auto',rows
    if len(g)>=len(entries):return'keep',rows
    if can_ask and not csb.ah_ask():return'auto',rows
    if can_ask and set(g)!=set(asked):return'ask',rows
    return'keep',rows

def tui_autohide_pending():
    return csb._AHQ[0]

def tui_autohide_answer(hide):
    q=csb._AHQ[0]
    if not q:return 0
    csb._AHQ[0]=None
    if hide:csb._AHOK[0]|=set(q['gone']);return len(q['gone'])
    csb._AHSEEN[0]=frozenset(q['gone']);return 0

def tui_autohide_ask(gone,rows,total):
    b=['%d of your %d local records are no longer on the server.'%(len(gone),total),
       'Hiding drops the record here (nothing is deleted on the server);',
       'records a snapshot still points at are kept either way.']
    for lab,i in rows:b.append('   %s   %s'%(lab,csb.short_id(i)))
    if len(gone)>len(rows):b.append('   ... and %d more'%(len(gone)-len(rows)))
    return b,['cancel - keep them','hide these %d'%len(gone)]

def tui_theme_cur(c=None):
    k=csb._theme_get(c or csb.cfg())
    if not isinstance(k,str):k='D02'
    k=k or'D02'
    k={'plain':'D02','green':'D03','neon':'D04o'}.get(k,k)
    return k if k in csb._THEMES else 'D02'

def tui_theme_step(c=None,cur=None):
    return csb._theme_step(c or csb.cfg(),cur)

def tui_theme_err():
    return csb._THEMEERR[0]

class _IntroCut(Exception):
    pass

_INTRO_TAIL=[None]
_ADOPT_SHOWN=[False]

def _raise_cut(dt):
    _INTRO_TAIL[0]=(time.time(),dt)
    raise _IntroCut()

def _intro_plan():
    p=[(0.25,1,0,None,0)]
    for i in range(9):p.append((ANIM,2,i+1,None,0))
    for r in range(1,cbar_rows()+1):p.append((ANIM,3,9,r,0))
    p.append((ANIM,4,9,INTRO_BAND,0))
    for k in range(len(VERN)+1):p.append((VER_ANIM,5,9,INTRO_BAND,k))
    return p

def _intro_st(st,nl,nr,nv):
    t=_INTRO_TAIL[0]
    if t is None:return st,nl,nr,nv
    if getattr(globals().get('u'),'modal',None) is not None:return st,nl,nr,nv
    el=time.time()-t[0];t1=t[1];acc=0.0;pick=None
    for d,s,n,r,v in _intro_plan():
        acc+=d
        if acc-t1<=el:pick=(s,n,r,v)
    if acc-t1<=el:
        _INTRO_TAIL[0]=None
        return st,nl,nr,nv
    return pick if pick else(st,nl,nr,nv)

def intro_cut(u,W,H,draw):
    try:intro(u,W,H,draw,True)
    except _IntroCut:
        t=getattr(u,'_term',None);p=(getattr(t,'pend',b'')or b'')if t is not None else b''
        if p and p[0]<0x80:t.pend=p[:1]

def _fetchfail(e):
    csb.errlog_append('=== %s ===\nfetch failed: %s\n\n'%(csb._disp(csb._now()),e))

def _st_head(w):
    _p=(w or'').split(':',1)[0].strip()
    return _p if 0<len(_p)<=48 and _p!=(w or'').strip() else w

def _vol_items(rows):return[(r['name'],r['name'])for r in rows]+[('(new volume, type a name)','__NEW__'),('(do not mount a volume)','')]
def _vol_ensure(t,v,u,draw,items):
    _now=_vol_rows(u)or[]
    if not any(r['name']==v or r['id']==v for r in _now):
        if not ask_yn(t,'create volume %s? (it does not exist yet)'%v,u,draw):
            u.status='cancelled: no volume created';return False
        run_op(t,csb.argv_vol_create(v),u,draw)
        _now=_vol_rows(u)or[]
        if not any(r['name']==v or r['id']==v for r in _now):return False
    items[:]=_vol_items(_now);u.volmap={r['name']:r['id']for r in _now};return True

def _child_env(u):
    env=dict(os.environ);env.update(CUBE_API_URL=u.c['api'],CUBE_API_KEY=u.c['key'],CSB_UI_NO_SPLASH='1',TERM='xterm-256color',CSB_DEV_PANEL='1',CSB_AUTO_NO_SPIN='1')
    if u.c.get('home')is None:env['CSB_REGISTRY']=u.c['reg']
    else:env.pop('CSB_REGISTRY',None)
    _ep=os.path.join(tempfile.gettempdir(),'csb-kind-%d-%d'%(os.getpid(),_KINDN[0]));_KINDN[0]+=1
    try:os.unlink(_ep)
    except Exception:pass
    env['CSB_ERR_KIND']=_ep;u.errd=_ep
    if u.c.get('aud')is not None:env['CSB_AUDIT']=u.c['aud']
    return env
_KINDN=[0]

def start_volumes_come_with(n):return(n or{}).get('kind')=='snap'
if __name__=='__main__':sys.exit(main())



#!/usr/bin/env python3
# csb - CubeSandbox CLI: the command layer (csb_tui renders, this does the work).
import re
def nseq_max(entries, fam):
    return max((e.get('nseq')or 0 for e in entries.values() if e.get('family')==fam),default=0)
def nseq_next(entries, hw, fam):
    n=max(nseq_max(entries,fam),(hw or{}).get(fam,0))
    taken={str(e.get('label')or'')for e in(entries or{}).values()}
    while label_default(fam,n+1)in taken:n+=1
    return n+1
def srv_nseq_max(c,fam):
    try:
        raw,full,why=_sb_list(c)
        if raw is None:
            try:raw=_Sandbox().list_v2(config=sdk(c))
            except Exception:return 0
        regs=reg(c)['entries']
        mx=0
        for s in[sb_from_raw(r,regs) for r in raw]:
            if s.get('family')==fam and s.get('nseq'):
                try:mx=max(mx,int(s['nseq']))
                except Exception:pass
        return mx
    except Exception:
        return 0
def label_default(fam, nseq) -> str:
    return '%s_%02d'%(fam,nseq)


def tpl_family(c,name):
    n=str(name or'')
    if re.fullmatch(r'snap-[0-9a-f]{24}',n):return n
    try:rows=tpl_rows(c)
    except Exception:return n
    if re.fullmatch(r'tpl-[0-9a-f]{24}',n):
        t=next((x for x in rows if x.get('id')==n),None)
        alias=(t or{}).get('alias')
        if not alias:return n
        return ((reg(c).get('templates')or{}).get(n)or{}).get('family') or alias
    t=next((x for x in rows if x.get('alias')==n and not x.get('is_snap')),None)
    if t:
        tid=t.get('id')or''
        fam=((reg(c).get('templates')or{}).get(tid)or{}).get('family')
        if fam:return fam
    return n
_CMIT=re.compile(r'^(.*)-commit-\d{8}(-\d+)?$')
def alias_hw_move(hw,old,new):
    if not old or not new or old==new:return None
    if old not in(hw or{}):return None
    try:o=int(hw.get(old)or 0);n=int(hw.get(new)or 0)
    except Exception:return None
    hw[new]=n if n else o;hw[old]=o;return hw[new]
def alias_has_resources(c,name):
    pre=str(name or'')+'_'
    if not name:return True
    try:
        for e in(reg(c).get('entries')or{}).values():
            if str(e.get('label')or'').startswith(pre):return True
    except Exception:pass
    try:
        for e in(led(c)or{}).values():
            if str(e.get('name')or'').startswith(pre):return True
    except Exception:pass
    return False
def alias_hw_reclaim(c,old):
    if not old or old=='' or not _sw('hw_reclaim'):return False
    try:
        if alias_has_resources(c,old):return False
    except Exception:return False
    try:
        hw=reg(c).setdefault('family_highwater',{})
        hw.pop(old,None)
        return True
    except Exception:return False
def ns_for(c,name):
    n=str(name or'')
    try:rows=tpl_rows(c)
    except Exception:rows=[]
    try:regs=reg(c) or{}
    except Exception:regs={}
    t=next((x for x in rows if x.get('id')==n and not x.get('is_snap')),None)
    if t is None:
        t=next((x for x in rows if (x.get('alias')or'')==n and not x.get('is_snap')),None)
    if t and t.get('alias'):
        al=t['alias']
        hw=regs.get('family_highwater')or{}
        fam=((regs.get('templates')or{}).get(t['id'])or{}).get('family')
        if _CMIT.match(al):
            return al,al
        if isinstance(hw,dict) and hw.get(al) is not None:
            return al,al
        f=fam or al
        if al!=f:
            return al,al
        return f,f
    f=tpl_family(c,n)
    return f,f
def lab_ok_name(s):
    t=s if isinstance(s,str)else''
    if len(t)<1 or len(t)>64:return False
    if re.fullmatch(r'[\w-]{1,64}',t,re.UNICODE):return True
    if not re.search(r'\w',t,re.UNICODE):return False
    return all(c in'_-'or c.isalnum()or unicodedata.category(c)in('Mn','Mc')for c in t)
def label_err(label, fam, entries):
    if label[:1] == '-':return'bad charset/length'
    if not lab_ok_name(label):return'bad charset/length'
    if any(e['family']==fam and e['label']==label for e in entries.values()):return'collision'
_MCODE={'130400':'MasterParamsError','130401':'AuthFailed','130404':'NotFound','130406':'NotFoundAtCubelet',
        '130408':'CubeletUnHealthy','130409':'Conflict','130429':'TooManyRequests','130480':'ConcurrentLimited',
        '130483':'InvalidParamFormat','130499':'ClientCancel','130519':'DiskNotEnough','130567':'HostDiskNotEnough',
        '130497':'ExecCommandInSandboxFailed','130568':'PreConditionFailed','130590':'UpdateNetworkFailed',
        '130592':'MasterRateLimitedError',
        '130593':'MasterInternalError','130594':'DBError','130595':'ReqCubeAPIFailed','130596':'ConnHostFailed',
        '130597':'SelectNodesNoRes','130598':'SelectNodesFailed','130599':'GWFailed'}
_NCODE=('130480','130483','130497','130519','130567','130568','130590')
_MTXT={'130400':'the server refused the request as invalid',
       '130401':'the API key was refused - check CUBE_API_KEY (csb help lists the env names)',
       '130404':'that object does not exist on the server',
       '130406':'the node that owns it no longer knows it - it may have been removed outside csb',
       '130408':'the node running that sandbox is unhealthy - check the cluster node named in the message',
       '130497':'the command could not run inside the sandbox - the guest agent did not come up',
       '130429':'the platform is rate limiting this client - wait a moment and retry',
       '130480':'the platform already runs too many of these - retry, or lower --concurrency',
       '130499':'the request was cancelled before the platform finished it',
       '130519':'the node is out of disk - free space, or ask for a smaller writable layer',
       '130567':'the host is out of disk - free space before retrying',
       '130568':'the platform refused it for the state that sandbox is in',
       '130590':'the platform could not apply the network change',
       '130592':'the platform is rate limiting this client - wait a moment and retry',
       '130593':'the master hit an internal error - that is the API side, retry in a moment',
       '130594':'the master could not read its own database - that is the API side, retry in a moment',
       '130595':'the master could not reach the API service - transient, retry in a moment',
       '130596':'the master could not reach the node that runs it - retry, or check the cluster',
       '130597':'no free capacity left',
       '130598':'the master could not pick a node for it - retry in a moment',
       '130599':'the platform gateway failed - transient, retry in a moment'}
_MCAUSE=(('130409',('active runtime ref','still has'),'a running clone still references that snapshot - wait for it to drain (~25-40s) or kill the clone'),
         ('130483',('snapshot catalog',),'the platform lost the pause catalog of that sandbox - its paused state cannot come back; kill it and start a new one'),
         ('130593',('pause','proxy','443'),'the platform proxy still holds the pre-pause route (often port 443 is taken)'))
def _cap_hint(why):
    if 'no free capacity' in why or '130597' in why:
        return ('\n  fix   free room: csb ls / csb kill <id> --yes;'
                ' or a smaller --n/--concurrency')
    return ''
_MNAME={v:k for k,v in _MCODE.items()if v not in('Conflict','NotFound','NotFoundAtCubelet')}
def _mcode_of(t):
    for code in _MCODE:
        if code in t:return code
    for name,code in _MNAME.items():
        if re.search(r'\b%s\b'%re.escape(name),t):return code
    return None
def _why_server(ex):
    t=str(ex)
    if 'is not running' in t:
        return ('node has no live runtime (master still says running) - '
                'pause/resume cannot fix it; csb info shows the state - the platform must restart the node')
    if 'add storages failed' in t or 'EBUSY' in t:
        return ('platform node storage is stuck (virtio_rw mount EBUSY) - not transient; clean the node mount or restart '
                'cube-agent on that node, then retry (other nodes may work)')
    code=_mcode_of(t)
    if code:
        name=_MCODE.get(code,'?')
        for c,fr,msg in _MCAUSE:
            if c==code and any(x in t for x in fr):return '%s (%s code %s %s)'%(msg,'node' if code in _NCODE else 'master',code,name)
        return '%s (%s code %s %s)%s'%(_MTXT.get(code,'the platform refused it'),'node' if code in _NCODE else 'master',code,name,_cap_hint(_MTXT.get(code,'')))
    if 'http 500' in t or 'error code -1' in t:
        return 'server failed to apply it (http 500, code -1) - likely transient; wait a few seconds, then retry'
    return t
def _sufless(existing, base, sep):
    existing=[x for x in existing if isinstance(x,str)]
    if not any(x==base or x.startswith(base+sep) for x in existing):return 0
    return max([1]+[int(x[len(base)+1:]) for x in existing if x.startswith(base+sep) and x[len(base)+1:].isdigit()])
def snap_name(src_label, date, existing) -> str:
    base='csb-%s_%s'%(src_label,date);m=_sufless(existing,base,'_')
    return base if not m else '%s_%d'%(base,m+1)
def tpl_alias(fam, date, existing):
    base='%s-commit-%s'%(fam,date);m=_sufless(existing,base,'-')
    return base if not m else '%s-%d'%(base,m+1)
def start_family(alias,tpl_entry=None):
    """The naming family of a sandbox started from a template is its **current alias**.

    Not the family recorded at commit time: that entry goes stale the moment the
    template is renamed (tpl alias), and new sandboxes then keep the old family."""
    return alias
def naming_fam(fam,is_snap,label,explicit=None):
    """For a snapshot start, an explicit --label prefix is the naming family.

    A sandbox renamed at creation (start <snap> --label cv_02) must clone into cv_03, not
    pi_11: when the caller gives an explicit label and no --family, the label prefix wins;
    the source family is kept in `ancestor` by the caller for lineage."""
    if not is_snap or explicit or not label or isinstance(label,list):return fam
    m=re.match(r'^([a-z0-9][a-z0-9-]*)_[0-9]+$',str(label))
    if not m:return fam
    return m.group(1)if(not fam or m.group(1)!=fam)else fam
def _reserve_labels(c,fam,n,key=None):
    key=key or fam
    p=(c or{}).get('reg');srv=srv_nseq_max(c,key);mine=(_reg or{}).get('family_highwater')or{}
    if not p:
        return label_batch((_reg or{}).get('entries')or{},dict(mine),key,n,srvn=srv)
    with _flock(p):
        disk=reg_read(p);hw=dict(disk.get('family_highwater')or{})
        for k,v in mine.items():
            try:hw[k]=max(int(v or 0),int(hw.get(k)or 0))
            except Exception:hw[k]=hw.get(k)or v
        labs=label_batch(disk.get('entries')or{},hw,key,n,srvn=srv)
        top=int(hw.get(key)or 0)
        for L in labs:
            try:top=max(top,int(str(L).rsplit('_',1)[1]))
            except Exception:pass
        hw[key]=top;disk['family_highwater']=hw
        if _reg is not None:_reg['family_highwater']=hw
        reg_write(p,disk)
    return labs
def label_batch(entries,hw,fam,n,srvn=0):
    if hw.get(fam,0)<srvn:hw[fam]=srvn
    j=[]
    for _ in range(n):
        ns=nseq_next(entries,hw,fam);j.append((label_default(fam,ns),ns));hw[fam]=ns
    return j
import json, os, datetime, time, unicodedata, threading
from collections import Counter
def reg_new():
    return{'version':1,'created':_now(),'family_highwater':{},'templates':{},'entries':{}}
_BAKW=set()
BAK_KEEP=3
def _baks(p):
    import glob
    return sorted(glob.glob(p+'.bak-*'))
def _bak(p,why):
    if p in _BAKW:return None
    _BAKW.add(p)
    try:
        with open(p,'rb') as s:raw=s.read()
        _prev=_baks(p)
        if _prev:
            try:
                with open(_prev[-1],'rb') as s:_last=s.read()
            except Exception:_last=None
            if _last==raw:
                err('warning: %s could not be read (%s)\n  %s already holds these exact bytes; started a new ledger'%(p,why,_prev[-1]))
                return _prev[-1]
        _ts=time.strftime('%Y%m%d-%H%M%S');_pre='%s.bak-%s-'%(p,_ts)
        _used=[int(x[len(_pre):])for x in _baks(p)if x.startswith(_pre)and x[len(_pre):].isdigit()]
        _n=(max(_used)+1)if _used else 0;b='%s%03d'%(_pre,_n)
        while os.path.exists(b):
            _n+=1;b='%s%03d'%(_pre,_n)
        with open(b,'wb') as d:d.write(raw)
        for _o in _baks(p)[:-BAK_KEEP]:
            try:os.remove(_o)
            except Exception:pass
        err('warning: %s could not be read (%s)\n  kept a copy at %s and started a new ledger'%(p,why,b))
        return b
    except Exception:
        err('warning: %s could not be read (%s) and could not be backed up - starting a new ledger'%(p,why))
        return None
_ROWW=set()
def _drop_rows(p,tbl):
    bad=[k for k,v in tbl.items() if not isinstance(v,dict)]
    for k in bad:tbl.pop(k,None)
    return len(bad)
def _dropwarn(p,n):
    if n and p not in _ROWW:
        _ROWW.add(p)
        err('warning: %s has %d damaged %s - dropped them, the rest of the ledger is intact'%(p,n,'record'if n==1 else'records'))
def _shape(p,obj,keys,what):
    if not isinstance(obj,dict):
        _bak(p,'%s, but not a json object'%what);return None
    for k in keys:
        v=obj.get(k)
        if v is None:obj[k]={}
        elif not isinstance(v,dict):
            _bak(p,'%s is %s, not a table'%(k,type(v).__name__));return None
    return obj
def led_read(p):
    try:r=jload(p)
    except Exception as e:
        _bak(p,_whyjson(e));return{}
    if r is None:return{}
    r=_shape(p,r,(),'a csb snapshot ledger')
    if r is None:return{}
    _dropwarn(p,_drop_rows(p,r))
    return r

def _whyjson(e):
    ln=getattr(e,'lineno',None)
    if ln is None:return '%s: %s'%(type(e).__name__,e)
    return 'not valid JSON (%s at line %s column %s)'%(getattr(e,'msg',e),ln,getattr(e,'colno',0))
def _hw_path(p):
    return os.path.join(os.path.dirname(os.path.abspath(p)),'highwater.json')
def _hw_read(p):
    m={}
    try:
        with open(_hw_path(p),encoding='utf-8')as f:d=json.load(f)
    except Exception:
        return m
    if not isinstance(d,dict):return m
    for k,v in d.items():
        if isinstance(v,int)and not isinstance(v,bool):m[k]=max(m.get(k,0),v)
    return m
def _hw_targets(p):return[_hw_path(p)]
def _hw_save(p,m):
    q=_hw_path(p)
    try:
        os.makedirs(os.path.dirname(q),exist_ok=True)
        _atomic_write(q,m)
    except Exception as ex:
        sys.stderr.write('warning: could not write the highwater file %s: %s\n'%(q,ex))
def _hw_write(p,d):
    if not d:return
    m=_hw_read(p)
    for k,v in d.items():m[k]=max(m.get(k,0),int(v or 0))
    _hw_save(p,m)
def _hw_set(p,d):
    if not d:return
    m=_hw_read(p)
    for k,v in d.items():m[k]=max(0,int(v or 0))
    _hw_save(p,m)
def reg_read(p):
    r=_reg_read_raw(p)
    hw=_hw_read(p)
    up={k:v for k,v in r['family_highwater'].items()if k not in hw}
    if up:_hw_write(p,up);hw.update(up)
    r['family_highwater']=dict(hw)
    return r
def _reg_read_raw(p):
    try:
        with open(p,encoding='utf-8') as f:r=json.load(f)
    except FileNotFoundError:return reg_new()
    except Exception as e:
        _bak(p,_whyjson(e));return reg_new()
    if not isinstance(r,dict)or r.get('version')!=1:
        _v=r.get('version')if isinstance(r,dict)else None
        if isinstance(_v,int)and not isinstance(_v,bool)and _v>1:
            _bak(p,'a newer csb wrote this registry (version %s)'%_v)
            _ROMODE[0]='the ledger was written by a newer csb (version %s) - csb reads it but will not write over it'%_v
            r=_shape(p,r,('family_highwater','templates','entries'),'a csb v1 registry')
            return r if r is not None else reg_new()
        _bak(p,'not a csb v1 registry');return reg_new()
    r=_shape(p,r,('family_highwater','templates','entries'),'a csb v1 registry')
    if r is None:return reg_new()
    r.setdefault('created',_now())
    _dropwarn(p,_drop_rows(p,r['entries'])+_drop_rows(p,r['templates']))
    for k in [k for k,v in r['family_highwater'].items() if not isinstance(v,int)or isinstance(v,bool)]:
        r['family_highwater'].pop(k,None)
    return r
def _atomic_write(p,obj):
    t='%s.tmp.%d.%d'%(p,os.getpid(),threading.get_ident())
    try:
        os.makedirs(os.path.dirname(os.path.abspath(p)),exist_ok=True)
        with open(t,'w',encoding='utf-8') as f:json.dump(obj,f,indent=1)
        os.replace(t,p)
    except Exception:
        try:os.unlink(t)
        except Exception:pass
        raise
_SW=(
 ('ui_box','CSB_UI_BOX',(),'choice','auto',('auto','ascii','unicode'),'ui',True,True,'frame charset'),
 ('ui_color','CSB_UI_COLOR',(),'choice',None,('auto','8','16','256','24'),'ui',True,True,'colour depth - unset means the terminal decides'),
 ('ui_panel_bg','CSB_UI_PANEL_BG',(),'bool',True,None,'ui',True,True,'panel background'),
 ('ui_no_splash','CSB_UI_NO_SPLASH',(),'bool',False,None,'ui',True,True,'skip the splash'),
 ('ui_no_sweep','CSB_UI_NO_SWEEP',(),'bool',False,None,'ui',True,True,'skip the sweep animation'),
 ('tui_force_redraw','CSB_TUI_FORCE_REDRAW',(),'bool',False,None,'tui',True,True,'redraw every frame'),
 ('tui_full_redraw_secs','CSB_TUI_FULL_REDRAW_SECS',(),'float',0.0,(0,None),'tui',True,True,'full redraw every N seconds'),
 ('tui_resync_sec','CSB_TUI_RESYNC_SEC',(),'float',300.0,(0,None),'tui',True,True,'full resync every N seconds'),
 ('tui_esc_wait','CSB_TUI_ESC_WAIT',(),'float',0.25,(0.0,None),'tui',True,True,'escape-sequence wait'),
 ('tui_sweep_wb','CSB_TUI_SWEEP_WB',(),'int',5,(1,None),'tui',True,True,'sweep band width'),
 ('tui_sweep_frames','CSB_TUI_SWEEP_FRAMES',(),'int',20,(4,None),'tui',True,True,'sweep frames'),
 ('tui_sweep_tick','CSB_TUI_SWEEP_TICK',(),'float',0.08,(0.02,0.25),'tui',True,True,'sweep tick seconds'),
 ('tui_sweep_sec','CSB_TUI_SWEEP_SEC',(),'float',60.0,(0.0,None),'tui',True,True,'sweep duration'),
 ('auto_hide','CSB_AUTO_HIDE',(),'bool',False,None,'auto',True,True,'auto-hide handled nodes'),
 ('auto_hide_ask','CSB_AUTO_HIDE_ASK',(),'bool',False,None,'auto',True,True,'ask before auto-hiding'),
 ('auto_no_adopt','CSB_AUTO_NO_ADOPT',(),'bool',False,None,'auto',True,True,'do not auto-adopt'),
 ('auto_no_seen','CSB_AUTO_NO_SEEN',(),'bool',False,None,'auto',True,True,'do not mark candidates as seen'),
 ('auto_no_spin','CSB_AUTO_NO_SPIN',(),'bool',False,None,'auto',True,True,'no spinner'),
 ('auto_proxy','CSB_AUTO_PROXY',(),'bool',True,None,'auto',True,True,'inject the host proxy into new sandboxes'),
 ('sbx_sweep','CSB_AUTO_SBX_SWEEP',(),'bool',True,None,'auto',True,True,'auto-reclaim dead sandbox policies on ls/start'),
 ('sbx_sweep_cooldown','CSB_AUTO_SBX_SWEEP_COOLDOWN',(),'int',600,(0,None),'auto',True,True,'seconds between two sightings before reclaim'),
 ('hw_reclaim','CSB_AUTO_HW_RECLAIM',(),'bool',True,None,'auto',True,True,'drop a renamed alias high-water key when nothing uses it'),
 ('dev_panel','CSB_DEV_PANEL',(),'bool',False,None,'dev',True,True,'panel mode (internal)'),
 ('dev_boot_msg','CSB_DEV_BOOT_MSG',(),'str',None,None,'dev',True,False,'boot message handoff (internal)'),
 ('cube_wait','CSB_WAIT',(),'int',240,(20,3600),'csb',False,True,'one-shot operation timeout'),
 ('cube_connect_wait','CSB_CONNECT_WAIT',(),'int',30,(5,300),'csb',False,True,'connect/handshake timeout'),
 ('cube_http_wait','CSB_HTTP_WAIT',(),'int',30,(10,120),'csb',False,True,'read-only HTTP call timeout'),
 ('cube_exec_wait','CSB_EXEC_WAIT',(),'int',600,(10,3600),'csb',False,True,'exec timeout'),
 ('shell_max','CSB_SHELL_MAX',(),'int',67108864,(1,None),'csb',True,True,'shell output warn line'),
 ('cube_stop_wait','CSB_STOP_WAIT',(),'int',120,(10,3600),'csb',False,True,'stop/kill timeout'),
 ('cube_tui_poll','CSB_TUI_POLL',(),'float',2.0,(0.25,3600.0),'csb',False,True,'TUI refresh interval'),
 ('cube_fetch_wait','CSB_FETCH_WAIT',(),'float',5.0,(0.5,3600.0),'csb',False,True,'fetch wait'),
 ('cube_fetch_giveup','CSB_FETCH_GIVEUP',(),'float',60.0,(0.5,3600.0),'csb',False,True,'fetch give-up'),
 ('cube_audit_max','CSB_AUDIT_MAX',(),'int',104857600,(None,None),'csb',False,True,'audit log rotate size'),
 ('cube_api_url','CUBE_API_URL',(),'str','http://127.0.0.1:3000',None,'official',False,False,'cluster API URL'),
 ('cube_api_key','CUBE_API_KEY',(),'str','e2b_000000',None,'official',False,False,'cluster API key'),
 ('cube_registry','CSB_REGISTRY',(),'str',None,None,'csb',False,False,'registry path override'),
 ('cube_audit','CSB_AUDIT',(),'str',None,None,'csb',False,True,'audit log path - empty means off'),
 ('cubemastercli','CSB_CUBEMASTERCLI',(),'str','cubemastercli',None,'csb',False,False,'CubeMaster CLI executable'),
 ('cubemaster_host','CSB_CUBEMASTER_HOST',(),'str',None,None,'csb',False,False,'CubeMaster address for the admin endpoint (default 127.0.0.1)'),
 ('cubemaster_port','CSB_CUBEMASTER_PORT',(),'str',None,None,'csb',False,False,'CubeMaster port for the admin endpoint (default 8089)'),
 ('net_ca','SSL_CERT_FILE',(),'str',None,None,'official',False,False,'CA bundle - environment only'),
 ('term','TERM',(),'str',None,None,'official',False,False,'terminal type'),
 ('term_program','TERM_PROGRAM',(),'str',None,None,'official',False,False,'terminal program'),
 ('colorterm','COLORTERM',(),'str',None,None,'official',False,False,'colour terminal hint'),
 ('no_color','NO_COLOR',(),'flag',False,None,'official',False,False,'disable colour when present'),
 ('xdg_config_home','XDG_CONFIG_HOME',(),'str',None,None,'official',False,False,'config root'),
 ('herdr_env','HERDR_ENV',(),'str',None,None,'official',False,False,'herdr marker'),
 ('herdr_workspace_id','HERDR_WORKSPACE_ID',(),'str',None,None,'official',False,False,'herdr workspace'),
 ('tmux','TMUX',(),'flag',False,None,'official',False,False,'tmux marker'),
 ('sty','STY',(),'flag',False,None,'official',False,False,'screen marker'),
)
_INF=float('inf')
_SWVAL={'ui_box':{'a':'ascii','1':'ascii','true':'ascii','utf8':'unicode','utf-8':'unicode',
                            'u':'unicode','0':'unicode','false':'unicode'}}
_SWM={r[0]:r for r in _SW}
_SWBY={}
_SWBYL={'box':'ui_box','color':'ui_color'}
for _r in _SW:
    _SWBY[_r[0].lower()]=_r[0];_SWBY[_r[1].lower()]=_r[0]
    for _a in _r[2]:_SWBY[_a.lower()]=_r[0]
del _r
def _sw_dir():
    rg=os.environ.get('CSB_REGISTRY')
    if rg:return os.path.dirname(os.path.abspath(rg))
    x=os.environ.get('XDG_CONFIG_HOME')
    hm=os.path.join(x if x and os.path.isabs(x) else os.path.expanduser('~/.config'),'csb')
    return os.path.join(hm,'config')
def _sw_path():return os.path.join(_sw_dir(),'switches.json')
_SWF=[None]
def _sw_read_file():
    try:
        with open(_sw_path(),encoding='utf-8') as f:d=json.load(f)
    except Exception:d=None
    return d if isinstance(d,dict)else{}
def _sw_data():
    if _SWF[0] is None:_SWF[0]=_sw_read_file()
    return _SWF[0]
_SWREADME=['csb switches - written by `csb config set`.',
           'Each key overrides the built-in default; `csb config unset <key>` removes it.',
           'State csb writes by itself lives in config.json, not here.']
_SWTRUE=('1',);_SWFALSE=('0',)
_SWW=[set()]
def _sw_warn(n,v,why):
    if(n,why)in _SWW[0]:return
    _SWW[0].add((n,why))
    try:sys.stderr.write('warning: %s=%r is %s - using the default\n'%(n,v,why))
    except Exception:pass
def _sw_bool(n,v,d,b=None):
    if v is None:return d
    s=str(v).strip().lower()
    if not s:return d
    if s in _SWTRUE:return True
    if s in _SWFALSE:return False
    _sw_warn(n,v,'not 1 or 0');return d
def _sw_int(n,v,d,b):
    if v is None:return d
    try:x=int(str(v).strip())
    except Exception:_sw_warn(n,v,'not a number');return d
    if b:
        lo,hi=b
        if lo is not None and x<lo:return lo
        if hi is not None and x>hi:return hi
    return x
def _sw_float(n,v,d,b):
    if v is None:return d
    try:x=float(str(v).strip())
    except Exception:_sw_warn(n,v,'not a number');return d
    if x!=x or x in(_INF,-_INF):return d
    if b:
        lo,hi=b
        if lo is not None and x<lo:return lo
        if hi is not None and x>hi:return hi
    return x
def _sw_choice(n,v,d,ch):
    if v is None:return d
    s=str(v).strip().lower()
    if s in ch:return s
    _sw_warn(n,v,'not one of %s'%'/'.join(ch));return d
def _sw_str(n,v,d,b=None):return d if v is None else str(v)
def _sw_flag(n,v,d,b=None):return v is not None and str(v) != ''
_SWP={'bool':_sw_bool,'int':_sw_int,'float':_sw_float,'choice':_sw_choice,'str':_sw_str,'flag':_sw_flag}
def _sw_src(key):
    r=_SWM[key];ty,df,b=r[3],r[4],r[5]
    v=None;o='default'
    if key in _SWOV:return _SWOV[key],'override'
    for n in(r[1],)+tuple(r[2]):
        if n not in os.environ:continue
        if _SWINJV.get(n)==os.environ[n]:continue
        v=os.environ[n];o='env';break
    if v is None:
        d=_sw_data()
        if key in d:v,o=d[key],'file'
        elif r[1] in d:v,o=d[r[1]],'file'
    if v is None:return df,'default'
    v=_SWVAL.get(key,{}).get(str(v).strip().lower(),v)
    return _SWP[ty](r[1],v,df,b),o
def _sw(key):return _sw_src(key)[0]
def _sw_rt(key,val,r):
    ty,df=r[3],r[4]
    if ty=='bool':
        if val:return'1'
        return'0' if df else None
    if ty=='flag':return'1' if val else None
    return None if val is None else str(val)
_SWINJV={};_SWOV={}
def _sw_inject():
    d=_sw_data()
    if not d:return
    for key,r in _SWM.items():
        if key not in d:continue
        val=_SWP[r[3]](r[1],d[key],r[4],r[5])
        txt=_sw_rt(key,val,r)
        if txt is None:continue
        for n in(r[1],)+tuple(r[2]):
            if n not in os.environ:os.environ[n]=txt;_SWINJV[n]=txt
def _prefs_refresh(c=None):
    p=prefs_path(c)
    if not os.path.exists(p):return
    d=prefs_read(c)
    if list(d.get('_readme')or[])==list(_PREFSREADME):return
    try:_pref_put(c,_readme=list(_PREFSREADME))
    except Exception as _e:_swallow('prefs refresh',_e)
def _sw_norm(key,val):
    r=_SWM[key];ty,ch=r[3],r[5]
    s=str(val).strip()
    m=_SWVAL.get(key,{}).get(s.lower())
    if m is not None:s=m
    if ty=='bool':
        if s.lower() in _SWTRUE or s.lower() in _SWFALSE:return s,''
        return None,'%s takes 1 or 0 (got %r)'%(r[1],val)
    if ty in('int','float'):
        try:x=float(s)
        except Exception:return None,'%s takes a number (got %r)'%(r[1],val)
        if x!=x or x in(_INF,-_INF):return None,'%s takes a finite number (got %r)'%(r[1],val)
        if ty=='int':
            try:int(s)
            except Exception:return None,'%s takes a whole number (got %r)'%(r[1],val)
        return s,''
    if ty=='choice':
        if s.lower() in ch:return s.lower(),''
        return None,'%s takes one of %s (got %r)'%(r[1],'/'.join(ch),val)
    return s,''

def _sw_set(key,val):
    r=_SWM.get(key)
    if r is None:return(False,'no such switch: %s'%key)
    if not r[8]:return(False,'%s comes from the environment - it is not stored in csb config'%r[1])
    v,why=_sw_norm(key,val)
    if why:return(False,why)
    try:os.makedirs(_sw_dir(),exist_ok=True)
    except Exception as e:return(False,'cannot write %s (%s)'%(_sw_path(),e))
    try:
        with _flock(_sw_path()):
            d=dict(_sw_read_file());d[key]=v
            d.setdefault('_readme',list(_SWREADME))
            _atomic_write(_sw_path(),d)
    except Exception as e:return(False,'cannot write %s (%s)'%(_sw_path(),e))
    _SWF[0]=d
    return(True,'ok')
def _sw_unset(key):
    if not os.path.exists(_sw_path()):return(True,'ok')
    try:os.makedirs(_sw_dir(),exist_ok=True)
    except Exception as e:return(False,'cannot write %s (%s)'%(_sw_path(),e))
    try:
        with _flock(_sw_path()):
            d=_sw_read_file()
            if key not in d:return(True,'ok')
            n=dict(d);n.pop(key)
            _atomic_write(_sw_path(),n)
    except Exception as e:return(False,'cannot write %s (%s)'%(_sw_path(),e))
    _SWF[0]=n
    return(True,'ok')
def _sw_reset_cache():_SWF[0]=None
_sw_inject()
def _reg_newer(p):
    try:
        with open(p,encoding='utf-8') as f:v=json.load(f).get('version')
    except Exception:return None
    return v if isinstance(v,int)and not isinstance(v,bool)and v>1 else None
def reg_write(p,r):
    _nv=_reg_newer(p)
    if _nv:
        die(2,_ROMODE[0] or 'the ledger was written by a newer csb (version %s) - csb reads it but will not write over it'%_nv)
    d=os.path.dirname(os.path.abspath(p));os.makedirs(d,exist_ok=True)
    _hw_write(p,r.get('family_highwater')or{})
    _atomic_write(p,{k:v for k,v in r.items()if k!='family_highwater'})
    if r.get('entries'):
        try:
            if os.path.exists(p+'.empty'):os.remove(p+'.empty')
        except Exception:pass
_REG_DEL=set();_TPL_DEL=set();_LED_DEL=set()
_REG_LOSTW=set()
def _lost_keys(want,got):
    g=set((got or {}).keys())
    return [k for k in want if k not in g]
def _lostwarn(p,what,lost,tries):
    if p+what in _REG_LOSTW:return
    _REG_LOSTW.add(p+what)
    err('warning: another csb process overwrote %s - %d %s lost in %d tries (%s.lock)'%(p,len(lost),what,tries,p))

import contextlib
_LOCKWARN=set()
def _lockwarn(p,e):
    if p in _LOCKWARN:return
    _LOCKWARN.add(p)
    err('cannot lock %s (%s) - concurrent csb may overwrite it'%(p,e))
@contextlib.contextmanager
def _flock(p):
    f=None;_lfail=None;_ld=None
    try:
        import fcntl as _fc
    except Exception:_fc=None
    if _fc is not None:
        try:
            os.makedirs(os.path.dirname(os.path.abspath(p)),exist_ok=True)
            f=open(p+'.lock','a',encoding='utf-8')
            _fc.flock(f,_fc.LOCK_EX)
        except Exception as _e:
            if f is not None:
                try:f.close()
                except Exception:pass
            f=None
            _lfail=_e
    if f is None:
        _lockwarn(p,_lfail or 'the fallback lock is unavailable')
    try:yield
    finally:
        if f is not None:
            try:
                import fcntl as _fc;_fc.flock(f,_fc.LOCK_UN)
            except Exception:pass
            try:f.close()
            except Exception:pass
        if _ld is not None:
            try:
                with open(os.path.join(_ld,'owner'),encoding='utf-8') as _f:_own=_f.read().strip()
            except Exception:_own=None
            if _own==_tok:
                try:os.rmdir(_ld)
                except Exception:pass
_SEEN={}
def _sec(p,s):return (os.path.abspath(p),s)
def _fp(v):
    return (v.get('ts'),v.get('label')or v.get('alias')or v.get('name')) if isinstance(v,dict) else None
def _seen_file(sec,tbl):
    _SEEN[sec]={k:_fp(v) for k,v in (tbl or {}).items()}
def _merge_cur(mine,disk,dels,sec=None):
    disk=disk or{}
    for k,v in disk.items():
        if k not in mine and k not in dels:mine[k]=v
    if sec is not None:
        seen=_SEEN.setdefault(sec,{})
        for k,v in list(mine.items()):
            if k in disk or k in dels:continue
            f=_fp(v)
            if f is not None and seen.get(k)==f:del mine[k]
        seen.update({k:_fp(v) for k,v in disk.items()})
    return mine
def resolve(arg,objs):
    ex=[o for o in objs if o['id']==arg]
    if ex:return ex
    if len(arg)>=24:
        pr=[o for o in objs if o['id'].startswith(arg)]
        if pr:return pr
    nm=[o for o in objs if o['label']==arg]
    if nm:
        die(2,'%s is a name, not an id - sandbox targets take the full id now:  %s'%(arg,'  '.join(sorted(str(o['id'])for o in nm))))
    return []
def _node(kind,label=None,id=None,**kw):
    n={'kind':kind,'label':label,'id':id,'state':None,'family':None,'parent':None,'stale':False,'orphan':False,'children':[]}
    n.update(kw);return n
TUI_SBKIND=('start','clone','from-snap','unknown')
def _gone_sb(key,n):
    _k=(n or{}).get('kind')
    if _k=='tpl-raw':return'%s needs a sandbox - this node is a template with no name (press A to name it)'%key
    if _k=='snap':
        _nm=(n or{}).get('label')or(n or{}).get('id')or''
        return'%s needs a sandbox - this node is a snapshot (run one from it:  csb start %s)'%(key,_nm or'<snapshot>')
    if not(n or{}).get('id'):return'%s needs a sandbox - this node is a group heading, not an object'%key
    if _k=='stale':return'%s needs a live sandbox - only a local leftover record is left (d drops it)'%key
    return'%s needs a live sandbox - %s'%(key,'this one is not in the local ledger, only a snapshot points at it'
        if(n or{}).get('external')else'this one was killed; only its snapshots are left here')

def short_id(x) -> str:
    x=str(x or'')
    for p in('snap-','tpl-'):
        if x.startswith(p)and len(x)>len(p)+8:return p+x[len(p):len(p)+8]
    return x[:8]
def _real_names(names,sid):
    return[x for x in(names or[])if x and x!=sid]

TUI_OT_RULES='-1 never  0 now  1 fastest  N idle s\n'
TMAX=2147483647
def timeout_err(t):
    s=str(''if t is None else t).strip()
    if not s:return 'required: seconds (0=now, -1=never, N=idle N s)'
    if s[0]=='+':s=s[1:]
    if s=='-1':return ''
    if s.startswith('-'):return 'timeout cannot be negative - use -1 for never'
    if not re.fullmatch(r'[0-9]+',s):return 'timeout must be an integer: 0 = now, -1 = never, N = seconds'
    if int(s)>TMAX:return 'timeout is too large: the platform takes at most %d seconds (about 68 years)'%TMAX
    return ''
def _tmo(o,dflt):
    if o.get('timeout')is None:return dflt
    e=timeout_err(o.get('timeout'))
    if e:die(2,'--timeout: %s'%e)
    return _int(o.get('timeout'),dflt,'--timeout')
TUI_BULK={'k':'kill','n':'snap','p':'pause','u':'resume','t':'timeout','c':'clone','d':'snaprm','A':'adopt'}
TUI_BULKNAME={'k':'kill','n':'snap','p':'pause','u':'resume','t':'timeout','c':'clone','d':'clean','A':'adopt','e':'exec'}
TUI_PERKEY={'exec','shell','logs','rb','commit','label-reset','alias','start'}
TUI_SKINEN={'D02':'obsidian','D04o':'synthwave','D14':'amber','D03':'matrix','D01':'paper'}
TUI_START_MAX=20
TUI_VOL_HINT=('<path in sandbox>:<volume>[ro]  e.g. /data:myvol  /data:myvolro (read-only)\n'
              'one mount per sandbox; the volume must exist (V).  Enter = skip')
CRW=74
CKVW=11
VOL_NAME_RULES='name: a-z A-Z 0-9 _ - up to 128 chars; the name BECOMES the volume id'
VOL_ID_RE=re.compile(r'^[a-zA-Z0-9_-]{1,128}$')
def crule(n=62):return ('-'if _ASC else'─')*n
def ckv(k,v):return '  %-*s  %s'%(CKVW,k,v)
VOL_WARN=('VOLUME: a filesystem outside every sandbox - only a',
          'sandbox can read or write it.  SNAPSHOT: rootfs + memory only;',
          'the volume and its files are NOT in it (platform v0.7.1+).',
          'MOUNT while CREATED only: csb start <tpl> --vol /data:<vol>;',
          'DETACH impossible: no API',
          '(PUT /sandboxes/{id}/volume answers 404).  SNAPSHOT revives',
          'the writer and mounts the SAME live volume - two writers corrupt',
          'files.  READ IT: csb cp <id>:/data .  DROP: csb kill <sandbox>',
          '--yes (volume outlives); REMOVE: csb vol rm <volume> --yes.')
VOL_HOT=('the volume and its files are NOT in it (platform v0.7.1+).',
         'DETACH impossible: no API',
         'the writer and mounts the SAME live volume - two writers corrupt')
def vol_warn_lines(panel=False,short=False):
    if short:return []
    return [(TUI_WARN if panel else '')+l if l in VOL_HOT else l for l in VOL_WARN]
def vol_warn(p=print):
    p('')
    for l in vol_warn_lines(False):p(l)
def vol_warn_short(p=print):
    p('')
    p('  no unmount, no rename; a snapshot holds no volume data')
    p('  more:  csb help vol   (or press V then Enter on a volume in the TUI)')
def tree_actions(n):
    d={}
    if not n:return d
    k=n.get('kind');st=n.get('state');sb=k in TUI_SBKIND and bool(n.get('id'))
    run=sb and st=='running';pa=sb and st=='paused'
    canstart=k=='tpl-root' or(k=='snap'and bool(n.get('id'))and not n.get('state'))
    d['exec']=run;d['shell']=run;d['clone']=run;d['snap']=run;d['commit']=run
    d['logs']=sb;d['url']=sb;d['timeout']=run;d['kill']=sb or k in('tpl-root','tpl-raw')
    d['rb']=(k in('snap','snap-root'))and bool(n.get('id'))
    d['pause']=run;d['resume']=pa;d['start']=canstart;d['label-reset']=k=='tpl-root'
    if k=='tpl-root'and n.get('deleted'):
        d['start']=False;d['label-reset']=False
    d['build']=True;d['theme']=True
    d['clean']=bool(n.get('id'))and((k=='snap'and snap_cleanable(n))or k=='snap-root' or k=='stale' or n.get('broken')or k=='dead')
    d['info']=sb or k in('tpl-root','tpl-raw')or(k=='snap'and bool(n.get('id')))or k=='stale' or k=='dead'
    d['mark']=d['range']=markable(n)
    d['alias']=k in('tpl-root','tpl-raw');d['volume']=True
    d['adopt']=(bool(n.get('id'))and bool(n.get('unadopted')or n.get('nolocal')))or(k=='unreg'and not n.get('id')and bool(n.get('children')))
    d['fold']=d['fold-all']=d['filter']=True
    d['help']=d['cmd']=d['quit']=True
    return d
def start_default_label(n):
    return (re.sub(r'[^a-z0-9]','',str((n or{}).get('id')).lower())[:12]or'snap')+'_01'
def bulk_labels(lab,n):
    if n<=1:return[lab]
    _b=lab if lab.endswith('_')else lab+'_'
    return[_b+'%02d'%i for i in range(1,n+1)]
def argv_start(n,lab,label=None,cnt=1,vol=None,ao=None,mode=None,no_dns=False,px=None):
    kd=(n or{}).get('kind')
    src=(n or{}).get('id')if kd=='snap' else lab
    a=['start',src]
    if mode=='inherit' and ao is not None:mode='on'
    if mode in('on','off'):a+=['--net',mode]
    if kd=='snap'and(n or{}).get('family'):a+=['--family',n['family']]
    if kd=='snap'and not(n or{}).get('family')and not label:label=start_default_label(n)
    if label:a+=['--label',label]
    try:c=int(cnt or 1)
    except Exception:c=1
    if c>1:a+=['--n',str(c)]
    if vol:a+=['--vol',vol,'--yes']
    if mode!='inherit' and ao is not None and mode!='off':a+=['--allow-out',(','.join(ao)if ao else'none')]
    if no_dns and ao and mode!='off':a+=['--no-dns']
    if px:a+=['--proxy',px]
    return a,c>TUI_START_MAX
def argv_adopt(n,name=None):
    i=(n or{}).get('id')or''
    if (n or{}).get('kind')=='unreg'and not i:return['adopt','--all']
    if (n or{}).get('kind')=='tpl-raw':return['tpl','alias',i,name]if name else['tpl','alias',i]
    return['adopt',i]+(['--as',name]if name else[])
def argv_resume(op,secs=None):
    _s=(secs or'').strip()
    return['resume',op]+(['--timeout',_s]if _s else[])+['--yes']
def argv_bulk(op,labels,secs=None):
    if op=='timeout':return [['timeout',L,secs] for L in labels] if secs else None
    return [[op,L]+(['--yes']if op in('kill','snap','snaprm','clean','clone')else[])for L in labels]
def argv_kill(label):return['kill',label,'--yes']
def argv_op(op,label):return argv_kill(label)if op=='kill'else[op,label]+(['--yes']if op in('pause','resume')else[])
def argv_snap(label,name=None):return['snap',label]+([name]if name else[])+['--yes']
def argv_clone(label,n=None):return['clone',label]+(['--n',str(n)]if str(n or'')not in('','1')else[])
def argv_commit(label,alias=None):return['commit',label]+(['--alias',alias]if alias else[])
def argv_rb(sbid,snapid):return['rb',sbid,snapid,'--yes']
def argv_timeout(label,secs):return['timeout',label,secs,'--yes']
def argv_label_reset(label,start=None):return['label-reset',label]+(['--start',start]if start else[])+['--yes']
def argv_alias(tid,alias):return['tpl','alias',tid,alias]
def argv_tpl_rm(label,yes=False):return['tpl','rm',label]+(['--yes']if yes else[])
def argv_tpl_build(image,alias=None):return['tpl','build','--image',image]+(['--alias',alias]if alias else[])
def argv_exec(label,argv):return['exec',label,'--']+list(argv)
def argv_vol_rm(name):return['vol','rm',name,'--yes']
def argv_vol_create(name,quiet=True,driver=None):return['vol','create',name]+(['--driver',driver]if driver else[])+(['--quiet']if quiet else[])
def vol_known(c):
    try:rows=vol_rows(c)
    except Exception:return None
    return None if rows is None else dict((r['name'],r['id'])for r in rows)
def vol_ro_choice(s):
    t=(s or'').strip().lower()
    if t in('y','yes'):return True,True,''
    if t in('n','no',''):return True,False,''
    return False,None,'read-only takes y or n - Enter means no, so %r is not an answer'%t
def vol_ro_chk(s):
    ok,_,why=vol_ro_choice(s)
    return ok,why
def vol_split(tok):
    t=(tok or'').strip()
    if t.endswith(':ro')and t.count(':')>1:return '','','write %sro - "ro" is a suffix of the volume name, not a third field'%t[:-3]
    if t.count(':')!=1:return '','','--vol needs exactly one colon: <path>:<volume>[ro]\n      example: --vol /data:ztvol\n      read-only: --vol /data:ztvolro'
    p,v=t.split(':',1)
    if not p.startswith('/'):return '','','the left side is the PATH INSIDE the sandbox and must start with "/"'
    if not v:return '','','the right side is the volume name or id - it cannot be empty'
    if len(v)==2 and v.endswith('ro'):return '','','volume name cannot be just "ro"'
    return p,v,''
def vol_reads_both(v,known):
    if not known or not(len(v)>2 and v.endswith('ro')):return False
    base=v[:-2]
    return(v in known or v in known.values())and(base in known or base in known.values())
def vol_mount_tok(tok,known=None):
    p,v,why=vol_split(tok)
    if why:return '','',False,why
    if not(len(v)>2 and v.endswith('ro')):return p,v,False,''
    base=v[:-2]
    if not known:return p,base,True,''
    if vol_reads_both(v,known):return '','',False,vol_amb_why(p,v,base,known)
    lit=v in known or v in known.values()
    return(p,v,False,'')if lit else(p,base,True,'')
def vol_amb_why(path,lit,cut,known):
    out=['ambiguous volume: %r and %r are both volumes'%(lit,cut)]
    for nm,ro in((lit,False),(cut,True)):
        s=vol_mount_str(path,nm,ro,known)
        out.append('  --vol %s   volume %r, %s'%(s,nm,'read-only'if ro else'writable')if s
                   else'  volume %r, %s:  nothing spells it - its id ends with "ro" too'%(nm,'read-only'if ro else'writable'))
    return '\n'.join(out)
def vol_mount_str(path,name,ro,known=None):
    for c in(name,(known or{}).get(name)):
        if not c:continue
        t='%s:%s%s'%(path or'/data',c,'ro'if ro else'')
        _p,v,why=vol_split(t)
        if why or vol_reads_both(v,known):continue
        cut=len(v)>2 and v.endswith('ro')
        if (v[:-2]if cut else v)==c and cut==ro:return t
    return ''
def vol_mount_arg(path,name,ro,known=None):
    t=vol_mount_str(path,name,ro,known)
    if t:return t,''
    if known is None:tail='the volume list did not arrive'
    elif not known:tail='the cluster has no volume at all - csb vol ls shows that, csb vol create <name> makes one'
    else:tail='its id ends with "ro" too'
    return '','cannot mount volume %r %s in a --vol - %s'%(name,'read-only'if ro else'writable',tail)
VOL_VM_CAP=3
def vol_miss_why(v,known,vm=''):
    if known is None or not v or v in known or v in known.values():return''
    t=(vm or'').strip()
    out=['start: no such volume %r -- csb vol ls lists them (a volume must exist before it can be mounted)'%v]
    syntax='  --vol is <path inside the sandbox>:<volume name>'
    if len(v)>2 and t.endswith('ro'):
        syntax+=', and a trailing "ro" means read-only - %r reads as the volume %r'%(t,v)
    out.append(syntax)
    nm=sorted(known)
    if nm:out.append('  csb vol ls lists %d: %s%s'%(len(nm),', '.join(nm[:VOL_VM_CAP]),
                                                    '  (+%d more)'%(len(nm)-VOL_VM_CAP)if len(nm)>VOL_VM_CAP else''))
    else:out.append('  csb vol ls lists none right now - csb vol create <name> makes one')
    return '\n'.join(out)
def vol_plan(pairs,known):
    out=[];taken={}
    for vm in pairs or[]:
        p,v,ro,why=vol_mount_tok(vm,known)
        if not why:why=vol_miss_why(v,known,vm)
        if not why and p in taken:
            why='two volumes on %r - one path holds one volume (%r already there)'%(p,taken[p])
        if why:return[],(vm,why)
        taken[p]=v
        out.append((p,v,(known or{}).get(v,v)or v,ro))
    return out,None
TUI_HELP_W=(9,15)
TUI_VAL='\ue001'
TUI_CEN='\ue000'
TUI_SEC='\ue002'
TUI_KV='\ue003'
def _ascii_out():
    enc=(getattr(__import__('sys').stdout,'encoding','')or'').lower().replace('-','')
    return enc in('ascii','usascii','ansi_x3.41968')
def _ev(k):return(os.environ.get(k)or'').strip().lower()
_TPREF={'iterm.app':(True,24),'vscode':(True,24),'vscode-insiders':(True,24)}
_UIP=[None]
def _box_auto():
    d=_TPREF.get(_ev('TERM_PROGRAM'))
    return bool(d[0])if d and d[0]is not None else _ascii_out()
def _box_pick():
    b=_sw('ui_box')
    return _box_auto()if b in(None,'auto')else b=='ascii'
def _box_env():return _box_pick()
def _box_ascii():return _box_pick()
_ASC=_box_env()
_ELT='...'if _ASC else'…'
TUI_WARN='\ue004'
HELP_W=76
TUI_HELP_ROWS=(
 ('NAV','↑ / ↓','move'),
 ('','PgUp / PgDn','+/-5 nodes (crosses parents)'if _ASC else'±5 nodes (crosses parents)'),
 ('','Home / End','first / last of the same type, this level'),
 ('','','tip: mark the first clone, End, then M = range'),
 ('','F5 / r','force refresh  (auto every 2s)'),
 ('BUILD','s start','new sandbox from this template / snapshot'),
 ('','c clone','copy a running sandbox (asks how many; Enter=1)'),
 ('','A adopt','name a sandbox or a nameless template'),
 ('','l label-reset','reset family numbering (template root)'),
 ('','a alias','rename the template (template root)'),
 ('','f commit','freeze a sandbox into a template (asks for a name)'),
 ('','B build','build a template from an image (asks image + alias)'),
 ('RUN','e exec','run one shell command'),
 ('','i shell','up to four ways: copy, tmux/screen, herdr, print'),
 ('SNAP','n snap','freeze a point (name is permanent)'),
 ('','','with a volume: snapshots keep no volume data'),
 ('','','a used name is refused - pick another one'),
 ('','b rb','roll back to this snapshot'),
 ('STATE','p pause','freeze it (a paused sandbox refuses ops)'),
 ('','u resume','unfreeze it'),
 ('','t timeout','idle timeout: 0 now / -1 never / N seconds'),
 ('','o logs','runtime log (clock noise filtered)'),
 ('','k kill','kill it (1 confirm); snapshots are NOT deleted'),
 ('','','on a template root: delete the template (1 confirm)'),
 ('DEL','d','delete this node (snapshot / [D] / [E] / stale)'),
 ('BULK','m mark','mark this node (sets the range anchor)'),
 ('','M range','select the span anchor -> cursor'),
 ('','','with >1 marked: k n p u t c d A e act on all of them'),
 ('','','type lock: mark sandboxes or snapshots, never both'),
 ('TREE','z','fold <-> pan mode'),
 ('','← / →','fold (on a leaf: its parent); pan mode: scroll'),
 ('','v','fold / unfold all groups here'),
 ('PANEL','V','volumes (Enter=info / d=delete / n=new / Esc=close)'),
 ('','/','filter nodes (any field)'),
 ('','T','cycle the 5 skins'),
 ('','?','this help'),
 ('','q','quit'),
 ('','','needs 45 cols x 6 lines, else one hint card'),
 ('POPUP','↑/↓ PgUp/PgDn','scroll in a popup (Done / Failed ends a run)'),
 ('','','every command opens in a popup over the tree.'),
 ('','','ESC closes it (Enter also works once it is done).'),
)
def _dupmark(nodes):
    labs={}
    for n in nodes:
        l=n.get('label')
        if l and _TUI.tui_mtyp(n)in('sb','unreg','snap'):labs[l]=labs.get(l,0)+1
    for n in nodes:
        l=n.get('label')
        n['_dup']=1 if(l and labs.get(l,0)>1 and _TUI.tui_mtyp(n)in('sb','unreg','snap'))else 0

_LASTRT=[None]
SBK=('start','clone','from-snap','unknown')
AUTOFOLD=12
def tree_sz(nd):
    return sum(1+tree_sz(n.get('children')or[])for n in nd)
def snap_cleanable(n):
    st=(n or{}).get('state')
    return not st or str(st).upper()in('READY','FAILED')
def markable(n):
    k=n.get('kind')
    return bool(n.get('id'))and(k in SBK or(k=='snap'and snap_cleanable(n))or k=='stale')
def row_match(n,f):
    if not f:return True
    s=' '.join(str(n.get(k)or'')for k in('label','id','state','kind','family','template','tpl','name','vols'))
    return f.lower() in s.lower()
_TZ=[None]
_TZL=[False]
_SKEW=[None]
_CFG=[None]
def _rawnow():return datetime.datetime.now(datetime.timezone.utc)
def _now():
    t=_rawnow()
    if _SKEW[0] is None and _CFG[0] is not None:_skew(_CFG[0])
    if _SKEW[0]:t-=datetime.timedelta(seconds=_SKEW[0])
    return t.strftime('%Y-%m-%dT%H:%M:%SZ')
def _svts(d):
    dd=d if isinstance(d,dict)else(getattr(d,'_data',None)or{})
    for k in('startedAt','started_at','createdAt','created_at'):
        if isinstance(dd,dict)and dd.get(k):return str(dd[k])
    return None
def _srv_started(c,ids):
    ids=set(ids);out={}
    for i in range(3):
        try:
            for r in _Sandbox().list_v2(config=sdk(c)):
                if r.get('sandboxID')in ids and r.get('startedAt'):out[str(r['sandboxID'])]=str(r['startedAt'])
        except Exception as _e:_swallow('server start',_e)
        if len(out)==len(ids)or i==2:break
        time.sleep(1.0)
    return out
def _srv_tpl_ts(c,tid,tries=3):
    for i in range(max(1,tries)):
        try:
            for t in tpl_rows(c):
                if t['id']==tid:return t['ts']
        except Exception:pass
        if i+1<max(1,tries):time.sleep(1.0)
    return None
def _tzoff():
    t=int((datetime.datetime.now().astimezone().utcoffset()or datetime.timedelta(0)).total_seconds())
    return '%s%02d:%02d'%('+'if t>=0 else'-',abs(t)//3600,abs(t)%3600//60)
def _nkey(n):
    try:return int(n.get('nseq')or 0)
    except Exception:return 0
def _iso(v):
    s=str(v).strip().replace('Z','+00:00').replace(' ','T',1)
    m=re.match(r'^(.*?\.)(\d+)(.*)$',s)
    return m.group(1)+(m.group(2)+'000000')[:6]+m.group(3)if m else s
def _tzload():
    if _TZ[0] is not None or _TZL[0]:return
    _TZL[0]=True
    try:reg()
    except Exception:pass
    finally:_TZL[0]=False
def _tkey(v):
    if not v:return 0.0
    try:
        d=datetime.datetime.fromisoformat(_iso(v))
        if d.tzinfo is None:
            _tzload();o=_TZ[0]or _tzoff();sg=1 if o[0]=='+'else-1
            d=d.replace(tzinfo=datetime.timezone(sg*datetime.timedelta(hours=int(o[1:3]),minutes=int(o[4:6]))))
        return d.timestamp()
    except Exception:return 0.0
def _ikey(n):
    return str(n.get('id')or n.get('label')or n.get('arg')or'')
def tree_key(n):
    t=_tkey(n.get('ts'))
    return(1,-t,_nkey(n),_ikey(n))if t else(0,0.0,_nkey(n),_ikey(n))
def tree_order(ns):
    return sorted(ns,key=tree_key)
def root_key(n):
    k=tree_key(n)
    return(n.get('kind')!='tpl-root',k[0]==0,k[1],k[2],k[3])
def _hum(v):
    if isinstance(v,str)and re.match(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}',v.strip()):return _disp(v.strip())
    return v
def _disp(v) -> str:
    k=_tkey(v)
    if not k:return str(v)if v else'-'
    d=datetime.datetime.fromtimestamp(k).astimezone();z=d.strftime('%z')
    return d.strftime('%Y-%m-%d %H:%M:%S')+' '+(z[:3]+':'+z[3:]if len(z)==5 else z)
def _skew(c=None):
    try:
        import urllib.request,email.utils
        c=c or cfg()
        rq=urllib.request.Request(c['api'].rstrip('/')+'/health',method='HEAD',headers={'X-API-Key':c['key']})
        with urllib.request.urlopen(rq,timeout=4)as r:h=r.headers.get('Date')
        if not h:return None
        off=int(round(time.time()-email.utils.parsedate_to_datetime(h).timestamp()))
        _SKEW[0]=0 if abs(off)<=5 else off
        return off
    except Exception:_SKEW[0]=0;return None
def clone_parent_id(tpl,ledger=None,snaporig=None):
    _t=str(tpl or'')
    _l=str(((ledger or{}).get(_t)or{}).get('origin')or'')
    _s=str((snaporig or{}).get(_t)or'')
    if _l and _s and _l!=_s:return None
    return _l or _s or None
def parent_names(regs,ledger,snaporig=None):
    _l={}
    for e in(regs or{}).values():
        _pl=(e or{}).get('parent')
        if not _pl or(e or{}).get('kind')!='clone':continue
        _o=clone_parent_id((e or{}).get('template_id'),ledger,snaporig)
        if _o:_l.setdefault(_o,set()).add(_pl)
    return {_i:next(iter(_s))for _i,_s in _l.items()if len(_s)==1}
def build_tree(sbs,tpls,reg,ledger,snaporig=None):
    regs=(reg or {}).get('entries',{}) or {}
    _famhw=(reg or{}).get('family_highwater')or{}
    tl={t['id']:t for t in tpls}
    roots=[];by_alias={};snaps={};raw=[]
    _ct=Counter(str(x.get('tpl')or'')for x in sbs if str(x.get('tpl')or'').startswith('snap-'))
    _ctpl={str(e.get('template_id'))for e in regs.values()if e.get('kind')=='clone'and str(e.get('template_id')or'').startswith('snap-')};_ctts={k:v for k,v in reversed(sorted(((str(v.get('template_id')),v.get('ts'))for v in regs.values()if v.get('kind')=='clone'and v.get('ts'))))}
    for t in tpls:
        if t['id'].startswith('snap-'):
            e=ledger.get(t['id'])or{};st=t.get('status')
            ok=st in(None,'READY')
            snaps[t['id']]=_node('snap',e.get('name')or t.get('alias')or t.get('name')or t['id'],t['id'],family=e.get('fam'),orphan=t['id'] not in ledger and ok,state=None if ok else st,ts=e.get('ts')or t.get('ts')or _ctts.get(t['id']),clonetemp=(_ct.get(t['id'],0)if t['id']in _ctpl else 0))
        elif t.get('alias'):
            _fx=((reg or {}).get('templates')or{}).get(t['id'],{}).get('family')or t['alias']
            _al=t['alias']
            if _CMIT.match(_al) or _famhw.get(_al)is not None:_k=_al;_pre=_al
            else:_k=_fx;_pre=_fx
            r=_node('tpl-root',_al,t['id'],family=_fx,ts=t.get('ts'),hw=_famhw.get(_k)or 0,next=label_default(_pre,nseq_next(regs,_famhw,_k)),deleted=t.get('deleted')or None);roots.append(r)
        else:
            raw.append(_node('tpl-raw',short_id(t['id']),t['id'],ts=t.get('ts'),unadopted=True))
    by_alias={r['label']:r for r in roots if r['kind']=='tpl-root'}
    by_tid={r['id']:r for r in roots if r['kind']=='tpl-root'}
    _alias={t['id']:t.get('alias')for t in tpls if t.get('alias')}
    _heal={}
    for _s in sbs:
        _f=((reg or {}).get('entries',{})or{}).get(_s['id'],{}).get('family')or''
        _a=_alias.get(_s.get('tpl')or'')or''
        if _f and _a and _f!=_a and _f not in by_alias and _a in by_alias:_heal[_f]=_a
    def fam(alias):return _heal.get(alias or'',alias or'')
    unreg=_node('unreg','no local name yet')
    stale=_node('stale','leftover record')
    main={}
    def lab(s):
        _e=regs.get(s['id'],{})or{}
        if _e.get('adopted')and _e.get('label'):return _e['label']
        return s.get('label')or _e.get('label')or s['id'][:8]
    def host_for(s):
        k=s.get('kind');par=s.get('parent');tid=s.get('tpl')
        if k=='start':
            _sn=snaps.get(tid)if str(tid or'').startswith('snap-')else None
            return (by_tid.get(tid)or by_alias.get(par)or by_alias.get(fam(par))
                    or by_alias.get(s.get('family'))or by_alias.get(fam(s.get('family')))
                    or by_alias.get(tl.get(tid,{}).get('alias'))or _sn)
        if k=='from-snap':return snaps.get(par)or snaps.get(tid)
        if k=='clone':
            return None
        t=tl.get(tid)
        if t and not str(tid).startswith('snap-'):return by_alias.get(t.get('alias'))
        if str(tid).startswith('snap-')and tid in snaps:return snaps[tid]
        return None
    _fsp=[]
    for s in sbs:
        k=s.get('kind');par=s.get('parent')
        h=host_for(s)
        n=_node(k or 'unknown',lab(s),s['id'],state=s.get('state'),family=s.get('family')or regs.get(s['id'],{}).get('family'),parent=par,ts=s.get('ts'),tpl=s.get('tpl'),nseq=s.get('nseq'),vols=s.get('vols'))
        n['unadopted']=not bool(s.get('label'))
        if not n['unadopted']and s['id'] not in regs:n['nolocal']=True
        if n['unadopted']:n['arg']=s['id']
        if n['kind']in TUI_SBKIND:n['arg']=s['id']
        if k=='from-snap' and h is None and s.get('ancestor'):
            h=by_alias.get(fam(s.get('ancestor')))
            if h is not None and par:n['broken']=True
        if k=='from-snap' and h is not None and h.get('kind')=='snap':_fsp.append((n,h))
        else:(h or unreg)['children'].append(n)
        main[s['id']]=n
    _LOS={v.get('origin')for v in ledger.values()if v}|{v for v in(snaporig or{}).values()if v}
    _SID={x.get('id')for x in sbs}
    _pn=parent_names(regs,ledger,snaporig)
    _dead=[]
    for sid,e in regs.items():
        if sid in main:continue
        if sid not in _LOS:continue
        g=_node('dead',e.get('label')or _pn.get(sid)or sid[:8],sid,family=e.get('family'),ts=e.get('ts'))
        _host=None;_k=e.get('kind')
        if _k=='from-snap' or (not _k and str(e.get('template_id')or'').startswith('snap-')):
            _host=snaps.get(str(e.get('parent')or e.get('template_id')or''))or snaps.get(str(e.get('template_id')or''))
        elif _k=='clone':
            _pid=clone_parent_id(e.get('template_id'),ledger,snaporig)
            if _pid:_host=main.get(_pid)
        if _host is None:_host=by_alias.get(fam(e.get('family')))
        (_host['children']if _host else roots).append(g);main[sid]=g;_dead.append((sid,e,g))
    for so,e2 in ledger.items():
        o=(e2 or{}).get('origin')
        if not o or o in main or o in regs:continue
        if o in _SID:continue
        g=_node('dead',_pn.get(o)or o[:8],o,external=True,ts=(e2 or{}).get('ts'));roots.append(g);main[o]=g
    for o in sorted(set((snaporig or{}).values())):
        if not o or o in main or o in regs:continue
        if o in _SID:continue
        g=_node('dead',_pn.get(o)or o[:8],o,external=True);roots.append(g);main[o]=g
    def _unlink(n):
        for r in list(roots):
            if r is n:roots.remove(n)
        for v in main.values():
            if n in(v.get('children')or[]):v['children'].remove(n)
    def _inside(a,b):
        return any(c is b or _inside(c,b) for c in(a.get('children')or[]))
    for _ in range(4):
        _moved=False
        for sid,e,g in _dead:
            _k=e.get('kind');_host=None
            if _k=='from-snap' or (not _k and str(e.get('template_id')or'').startswith('snap-')):
                _host=snaps.get(str(e.get('parent')or e.get('template_id')or''))or snaps.get(str(e.get('template_id')or''))
            elif _k=='clone':
                _pid=clone_parent_id(e.get('template_id'),ledger,snaporig)
                if _pid:_host=main.get(_pid)
            if _host is None or _host is g:continue
            if g in(_host.get('children')or[]):continue
            if _inside(g,_host):continue
            _unlink(g);_host['children'].append(g);_moved=True
        if not _moved:break
    _IX={}
    for _k,_v in main.items():
        for _q in(_v['label'],_k):
            if _q not in _IX:_IX[_q]=_v
    for s in sbs:
        if s.get('kind')=='clone':
            n=main[s['id']];pl=s.get('parent')
            p=_IX.get(pl)
            if p is not None:
                n['broken']=False
                if n in unreg['children']:unreg['children'].remove(n)
                p['children'].append(n)
            elif s.get('ancestor')and by_alias.get(s['ancestor'])is not None:
                h=by_alias[s['ancestor']]
                _pid=clone_parent_id((regs.get(s['id'])or{}).get('template_id')or s.get('tpl'),ledger,snaporig)
                _g=main.get(_pid)if _pid else None
                if _g is None:
                    if pl:n['broken']=True
                    if n in unreg['children']:unreg['children'].remove(n)
                    h['children'].append(n)
                else:
                    if n in unreg['children']:unreg['children'].remove(n)
                    _g['children'].append(n)
            else:
                if n not in unreg['children']:unreg['children'].append(n)
    for n in raw:
        if n not in unreg['children']:unreg['children'].append(n)
    unatt=_node('snap-root','unattached snapshots')
    for sid,sn in sorted(snaps.items(),key=lambda kv:tree_key(kv[1])):
        _e=ledger.get(sid)or{}
        org=_e.get('origin')or(snaporig or{}).get(sid)
        _f=(_e.get('fam')or'')if _e.get('adopted')else''
        _h=(by_alias.get(_f)or by_alias.get(fam(_f)))if _f else None
        _o=main.get(org)if org else None
        if _o is not None and not(_e.get('adopted')and _o.get('external')):
            _o['children'].append(sn);sn['orphan']=False
        elif _h is not None:
            _h['children'].append(sn);sn['orphan']=False
        elif _o is not None:
            _o['children'].append(sn);sn['orphan']=False
        else:
            sn['orphan']=sn['orphan']or not sn.get('state');unatt['children'].append(sn)
    for n,sn in _fsp:sn['children'].append(n)
    if unatt['children']:roots.append(unatt)
    for sid,e in regs.items():
        if sid not in main:stale['children'].append(_node('stale',e.get('label')or sid[:8],sid,stale=True,family=e.get('family'),ts=e.get('ts')))
    for _n in unreg['children']:_n['unreg1']=True
    out=roots+([unreg]if unreg['children'] else[])+([stale]if stale['children']else[])
    _UR={'tpl-raw':0,'tpl-root':0,'start':1,'clone':1,'from-snap':1,'unknown':1,'snap':2,'snap-root':2}
    def _order(ns):
        for n in ns:
            if n.get('children'):
                if n is unreg:
                    n['children']=sorted(n['children'],key=lambda x:(_UR.get(x.get('kind'),3),tree_key(x)))
                else:
                    n['children']=tree_order(n['children'])
                _order(n['children'])
    out.sort(key=root_key)
    _order(out)
    for _n in _allnodes(out):_n['actions']=tree_actions(_n)
    return out
BOOL=('h','yes','dry-run','debug','async','no-net','force','all','quiet','list','undo','ledger','hard','entries','policies','allow-dns','no-dns','no-internet','probe')
_NEEDV={'label','env','meta','vol','net','proxy','timeout','on-timeout','n','concurrency','family','as',
        'alias','image','disk','mem','out','via','sig','driver','start','o','dns-server','deny-out','node'}
def _flagval(k,v):
    return False if k in BOOL and isinstance(v,str) and v.strip().lower() in('false','0','no','off')else v
_NVAL=re.compile(r'-[0-9]')
def _vval(a):
    return not a.startswith('-')or bool(_NVAL.match(a))
_KNOWN_FLAGS=set('''_ tail alias all allow-out as async concurrency cpu debug disk driver dry-run
family fix force h hard image label ledger list mem n net no-net o on-timeout out proxy quiet sig start timeout undo via
yes env meta vol version entries policies allow-dns no-dns dns-server deny-out no-internet probe node'''.split())
def parse(argv):
    if not argv:return('',{'_':[]})
    cmd=argv[0];o={'_':[]}
    i=1;dd=False
    while i<len(argv):
        a=argv[i]
        if dd:o.setdefault('tail',[]).append(a);i+=1;continue
        if a=='--':dd=True
        elif a.startswith('--'):
            k=a[2:];v=True
            if k=='help':k='h'
            if k=='allow-out' and i+1<len(argv)and argv[i+1]=='-':v='-';i+=1
            elif '=' in k:k,v=k.split('=',1)
            elif k not in BOOL and i+1<len(argv)and(_vval(argv[i+1])):v=argv[i+1];i+=1
            v=_flagval(k,v)
            if v is True and k in _NEEDV:die(2,'%s needs a value%s'%(a.split('=')[0],' (next: %r is a flag)'%argv[i+1]if i+1<len(argv)else''))
            if k=='o' and v!='json':die(2,'-o only accepts json (got %r)'%v)
            o[k]=v if k not in o else([o[k]]if not isinstance(o[k],list)else o[k])+[v]
        elif a.startswith('-')and a[1:].isdigit():
            o['_'].append(a)
        elif a.startswith('-')and len(a)==2:
            k=a[1];v=True
            if k not in BOOL and i+1<len(argv)and(_vval(argv[i+1])):v=argv[i+1];i+=1
            v=_flagval(k,v)
            if v is True and k in _NEEDV:die(2,'%s needs a value%s'%(a.split('=')[0],' (next: %r is a flag)'%argv[i+1]if i+1<len(argv)else''))
            if k=='o' and v!='json':die(2,'-o only accepts json (got %r)'%v)
            o[k]=v if k not in o else([o[k]]if not isinstance(o[k],list)else o[k])+[v]
        else:o['_'].append(a)
        i+=1
    return(cmd,o)
def exit_code(kind):return{'ok':0,'cancel':1,'usage':2,'runtime':3}[kind]
def wait_poll(fetch,want,maxpolls,interval):
    import time
    for _ in range(maxpolls):
        if fetch()==want:return(True,'ok')
        if interval:time.sleep(interval)
    return(False,'timeout')
def colorize(tty,nocolor,term):
    return bool(tty and not nocolor and term and term!='dumb')
import os,subprocess,sys,json as _json,shlex;sys.modules.setdefault('csb',sys.modules['__main__'])if __name__=='__main__'else None
try:__version__=__import__('importlib.metadata',fromlist=['version']).version('csbtui')
except Exception:__version__='0.1.0'
def _env(*ks):return next((os.environ[k] for k in ks if k in os.environ),None)
def cfg() -> dict:
    api=_env('CUBE_API_URL')or'http://127.0.0.1:3000'
    key=_env('CUBE_API_KEY')or'e2b_000000'
    _xdg=_env('XDG_CONFIG_HOME')
    _hm=os.path.join(_xdg if _xdg and os.path.isabs(_xdg) else os.path.expanduser('~/.config'),'csb')
    _lg=os.path.join(_hm,'ledger');_cf=os.path.join(_hm,'config');_lo=os.path.join(_hm,'log')
    _ex=_env('CSB_REGISTRY')
    if _ex:
        reg=_ex;_cf=_rd=os.path.dirname(os.path.abspath(reg));_lo=_cf
    else:
        reg=os.path.join(_lg,'sandbox-registry.json')
    _rp=os.path.abspath(reg);_rb=os.path.basename(_rp);_rd=os.path.dirname(_rp)
    led=(os.path.join(_rd,'.csb-snapshots.json')if _rb=='sandbox-registry.json'
         else os.path.join(_rd,'%s.csb-snapshots.json'%os.path.splitext(_rb)[0]))
    _np=os.path.join(_cf,'config.json')
    _ne=os.path.join(_lo,'tui-error.log')
    _na=os.path.join(_lo,'audit.log')
    a=_env('CSB_AUDIT')
    aud=None if a=='' else(a or _na)
    ca=_env('SSL_CERT_FILE')or next((p for p in('/root/.local/share/mkcert/rootCA.pem',os.path.expanduser('~/cube-rootCA.pem'))if os.path.exists(p)),None)
    for _d in (_cf,_lg,_lo):
        try:os.makedirs(_d,exist_ok=True)
        except Exception:pass
    c={'api':api,'key':key,'reg':reg,'led':led,'aud':aud,'ca':ca,
       'pref':_np,'err':_ne,
       'home':None if _ex else _hm};_CFG[0]=c
    return c
def errlog():
    return cfg().get('err')or os.path.join(os.path.dirname(os.path.abspath(cfg()['reg'])),'tui-error.log')
LOGKEEP=10
ERRLOG_MAX=100*1024*1024
def _log_rotate(p,maxbytes=ERRLOG_MAX,keep=LOGKEEP):
    try:
        if not os.path.exists(p)or os.path.getsize(p)<=maxbytes:return False
        _d=os.path.dirname(p)or'.';_b=os.path.basename(p)
        _ex=sorted(int(n.rsplit('.',1)[1])for n in os.listdir(_d)
                   if n.startswith(_b+'.bak.')and n.rsplit('.',1)[1].isdigit())
        _n=(_ex[-1]if _ex else 0)+1
        os.replace(p,'%s.bak.%d'%(p,_n))
        _ex.append(_n)
        for _i in _ex[:-keep]:
            try:os.remove('%s.bak.%d'%(p,_i))
            except Exception:pass
        return True
    except Exception:return False
def errlog_append(txt):
    p=errlog()
    try:
        os.makedirs(os.path.dirname(os.path.abspath(p)),exist_ok=True)
        _log_rotate(p,ERRLOG_MAX)
        with open(p,'a',encoding='utf-8')as f:f.write(txt)
        return p
    except Exception:return None
CMH=_env('CSB_CUBEMASTER_HOST')or'127.0.0.1'
CMP=_env('CSB_CUBEMASTER_PORT')or'8089'
def cm_addr():return['-a',CMH,'-p',CMP]
def cm_txt():return'-a %s -p %s'%(CMH,CMP)
def set_alias_cli(c,tid,alias):
    exe=_env('CSB_CUBEMASTERCLI')or'cubemastercli'
    try:p=subprocess.run([exe]+cm_addr()+['template','set-alias','--template-id',tid,'--alias',alias,'--json'],capture_output=True,text=True,timeout=_stop_secs())
    except FileNotFoundError:die(3,'%s not found: install CubeMaster CLI (see INSTALL.md)'%exe)
    except subprocess.TimeoutExpired:die(3,'set-alias timed out after %ds (raise CSB_STOP_WAIT)'%_stop_secs())
    blob=(p.stdout or '')+(p.stderr or '')
    if p.returncode!=0:
        if 'template not found' in blob.lower():
            die(2,'%s has no template record on CubeMaster (a FAILED build leaves only a job)'%short_id(tid)
                +'\nfix   csb tpl rm %s --yes, or rebuild: tpl build --image <ref> --alias <name>'%tid)
        _m='%s alias failed (%s)'%(short_id(tid),(blob.strip()or'(no reason given by the server)')[:400])
        die(3,_m+' - run:  %s set-alias %s --alias %s'%(cm_txt(),tid,alias))
    try:return json.loads((p.stdout or'').strip()or'{}')
    except Exception:return{'raw':blob.strip()}
def sdk_conf(c=None):
    c=c or cfg()
    if c['ca'] and not os.environ.get('SSL_CERT_FILE'):os.environ['SSL_CERT_FILE']=c['ca']
    from cubesandbox import Config
    return Config(api_url=c['api'],api_key=c['key'])
def jload(p):
    if not os.path.exists(p):return None
    with open(p,encoding='utf-8') as f:return _json.load(f)
def out(o):
    if isinstance(o,(dict,list)):_json.dump(o,sys.stdout,ensure_ascii=False,indent=1);sys.stdout.write('\n')
    else:print(o)
def _net_hint(msg):
    if 'Connection refused' in msg or 'Max retries exceeded' in msg or 'NewConnectionError' in msg:
        return '\n  cannot reach the server - check CUBE_API_URL, or that the API is up (the request never left this machine)'
    if 'timed out' in msg or 'Timeout' in msg:
        return '\n  the server did not answer in time - retry, or check the API host'
    mc=_SRV_CODE.search(msg)
    if mc and int(mc.group(1))>=500:
        mm=_SRV_MSG.search(msg)
        return ('\n  the server itself failed (HTTP %s: %s) - that is the API side, not your command;'
                ' retry in a moment, and check its logs if it keeps happening')%(mc.group(1),(mm.group(1) if mm else '')or 'no message')
    if ('Expecting value' in msg or 'JSONDecodeError' in msg) and ('failed:' in msg or 'ApiError' in msg):
        return ('\n  what came back was not JSON - a proxy or an error page answered instead of the API;'
                ' check CUBE_API_URL, or that the API is up')
    return ''
_SRV_CODE=re.compile(r'"code"\s*:\s*(\d{3})')
_SRV_MSG=re.compile(r'"message"\s*:\s*"([^"]{0,120})"')
def err(msg):
    _s=_nump(msg)+_net_hint(str(msg));_W=_termw()
    if _W and any(_dw(_cln(x))>_W for x in _s.split('\n')):
        print('\n'.join(y for _x in _s.split('\n')for y in _foldlines(_x,_W)),file=sys.stderr)
    else:print(_s,file=sys.stderr)
def die(code,msg,raw=None,kind=None):
    if _JSONMODE[0]:
        try:out_json(_err_obj(code,msg,raw,kind))
        except Exception:pass
    _kf=os.environ.get('CSB_ERR_KIND')
    if kind and _kf:
        try:
            with open(_kf,'a',encoding='utf-8')as _k:_k.write(kind+'\n')
        except Exception:pass
    err(msg);sys.exit(code)
def is_tty():
    try:return sys.stdin.isatty()
    except Exception:return False
def _yn(msg):
    while True:
        a=input('%s [y/N] '%_nump(msg)).strip().lower()
        if a in('y','yes'):return True
        if a in('','n','no'):return False
        if not is_tty():return False
        err('type y or n (Enter = no)')
def color_ok(c):
    c=c or cfg();return colorize(is_tty(),_env('NO_COLOR'),_env('TERM')or '')
_ACTL=re.compile(r'[\x00-\x1f\x7f]')
_AQW=" \t\r\n\v\f\"'\\"
def _aarg(x):
    s=_ACTL.sub(lambda m:'\\x%02x'%ord(m.group(0)),str(x))
    return shlex.quote(s) if any(ch in _AQW for ch in s) else s
_AUDHIDE=('--env','--meta')
def _audargs(args):
    out=[];hide=False
    for x in args:
        s=str(x)
        if hide:out.append('***');hide=False;continue
        if s in _AUDHIDE:hide=True;out.append(_aarg(x))
        elif any(s.startswith(p+'=')for p in _AUDHIDE):out.append(s.split('=',1)[0]+'=***')
        else:out.append(_aarg(x))
    return' '.join(out)
def _audit(args,rc):
    p=None
    try:
        p=cfg().get('aud')
        if not p:return
        os.makedirs(os.path.dirname(os.path.abspath(p)),exist_ok=True)
        try:
            _log_rotate(p,_sw('cube_audit_max'))
        except Exception as e:_audwarn(p,'rotate',e)
        with open(p,'a',encoding='utf-8') as f:
            f.write('%s %s %s\n'%(_now(),_audargs(args) or 'tui',rc))
    except Exception as e:_audwarn(p,'write',e)
_PREFK=('tzoff','auto_seen','noauto','allow_out','allow_out_hist','allow_dns','dns_server','proxy_url','proxy_hist','egress_last')
_PREFLK=threading.Lock()
_PREFSREADME=[
  "csb prefs - the only file here meant to be edited by hand. csb writes it itself;",
  "hand edits are safe (a broken format is treated as if the file were absent).",
  "Preferences live here. State (names / families / lineage / snapshot origins) lives in",
  "sandbox-registry.json and .csb-snapshots.json next to it.",
  "Behaviour switches live in switches.json (written by `csb config set <name> <value>`),",
  "not here and not in the program: the built-in default for every switch is declared once in",
  "the _SW table inside csb.py (name / type / default / description), and the value",
  "you store only overrides it. Precedence is always: command line flag > environment variable >",
  "switches.json > built-in default. New names look like CSB_UI_BOX, and that is the only",
  "spelling. Run `csb config list` for the full table and where each value came from.",
  "Keys: theme = the skin picked last (the TUI writes it when you press T); tzoff = the local UTC offset; auto_seen = sandbox ids already auto-adopted (append-only,",
  "so a sandbox announced long ago may be announced once more after 1000 newer ones);",
  "allow_out = the outbound CIDRs/domains picked last time (comma separated);",
  "allow_out_hist = the most recent groups (at most 5, newest first);",
  "proxy_url = the proxy picked last time (empty = none);",
  "proxy_hist = the proxy URLs used so far (newest first, kept until deleted in the picker);",
  "allow_dns = kept for compatibility (the TUI DNS page was removed; whitelist DNS follows the list);",
  "dns_server = the resolver to allow with the whitelist (empty = read it from the sandbox; --no-dns keeps DNS blocked);",
  "egress_last = the network combination (mode / allow_out / dns / proxy) used last time;",
  "vol_last = the last volume mount the TUI used (name / path / ro), offered as the '(same as last time: ...)' entry right above '(do not mount a volume)'."
 ]
def prefs_path(c=None):
    return (c or cfg()).get('pref')or os.path.join(os.path.dirname(os.path.abspath((c or cfg())['reg'])),'config.json')
def prefs_read(c=None):
    try:
        with open(prefs_path(c),encoding='utf-8') as f:d=json.load(f)
    except Exception:
        return {}
    return d if isinstance(d,dict) else {}
def prefs(c=None):
    d=prefs_read(c);r=reg(c)
    for k in _PREFK:
        if k not in d and r.get(k)is not None:d[k]=r[k]
    return d
def _pref_put(c=None,**kw):
    c=c or cfg()
    p=prefs_path(c)
    os.makedirs(os.path.dirname(os.path.abspath(p)),exist_ok=True)
    kw.setdefault('_readme',list(_PREFSREADME))
    with _PREFLK,_flock(p):
        d=prefs_read(c);d.update(kw);d.setdefault('version',1);_atomic_write(p,d)
    return d
def save_prefs(c=None,**kw):
    p=prefs_path(c)
    try:return _pref_put(c,**kw)
    except Exception as e:
        _prefwarn(p,e);return {}
_reg=None;_led=None
def reg(c=None):
    global _reg
    if _reg is None:
        c=c or cfg()
        p=c['reg'];_reg=reg_read(p)
        _seen_file(_sec(p,'entries'),_reg.get('entries'));_seen_file(_sec(p,'templates'),_reg.get('templates'))
    _TZ[0]=prefs_read(c).get('tzoff')or _reg.get('tzoff')
    return _reg
def _bust():
    global _reg,_led
    _reg=None;_led=None
def save_reg(c=None):
    global _reg;c=c or cfg();p=c['reg']
    if _reg is None:_reg=reg(c)
    for _try in range(4):
      with _flock(p):
        if _try:_SEEN.pop(_sec(p,'entries'),None);_SEEN.pop(_sec(p,'templates'),None)
        disk=reg_read(p)
        if not _reg.get('tzoff')and not disk.get('tzoff')and not prefs_read(c).get('tzoff'):save_prefs(c,tzoff=_tzoff())
        _merge_cur(_reg.setdefault('entries',{}),disk.get('entries'),_REG_DEL,_sec(p,'entries'))
        _merge_cur(_reg.setdefault('templates',{}),disk.get('templates'),_TPL_DEL,_sec(p,'templates'))
        _merge_cur(_reg.setdefault('family_highwater',{}),disk.get('family_highwater'),set())
        reg_write(p,_reg)
        _w=reg_read(p);_seen_file(_sec(p,'entries'),_w.get('entries'));_seen_file(_sec(p,'templates'),_w.get('templates'))
      _want=list(_reg.get('entries')or{})+list(_reg.get('templates')or{})
      _chk=reg_read(p)
      _lost=[k for k in _want if k not in set((_chk.get('entries')or{}).keys())|set((_chk.get('templates')or{}).keys())]
      if not _lost:break
      import time as _tm;_tm.sleep(0.05)
    else:_lostwarn(p,'registry',_lost,4)
def led(c=None):
    global _led
    if _led is None:
        p=(c or cfg())['led'];_led=led_read(p)
        _seen_file(_sec(p,'led'),_led)
    return _led
def save_led(c=None):
    global _led;p=(c or cfg())['led'];os.makedirs(os.path.dirname(os.path.abspath(p)),exist_ok=True)
    if _led is None:
        _led=led(c)
        if not _led:return
    for _try in range(4):
      with _flock(p):
        if _try:_SEEN.pop(_sec(p,'led'),None)
        _merge_cur(_led,led_read(p),_LED_DEL,_sec(p,'led'))
        _atomic_write(p,_led)
        _seen_file(_sec(p,'led'),led_read(p))
      _lost=_lost_keys(_led,led_read(p))
      if not _lost:break
      import time as _tm;_tm.sleep(0.05)
    else:_lostwarn(p,'snapshot ledger',_lost,4)
def is_json(o):return o.get('o')=='json' if isinstance(o,dict) else False
_JSONMODE=[False]
def _err_obj(code,msg,raw=None,kind=None):
    e={'code':code,'message':msg}
    if raw:e['server']=str(raw)
    if kind:e['kind']=kind
    return {'error':e}
def confirm(o,msg,why=None):
    if o.get('dry-run'):
        _w=why or msg.rstrip('? ')
        if is_json(o):out_json({'dry_run':True,'action':_w})
        else:sys.stdout.write('dry-run: %s%s - nothing was changed\n'%(msg.rstrip('? '),((' [%s]'%why)if why else'')))
        sys.exit(0)
    if o.get('yes'):return True
    if not is_tty():die(2,'--yes required for %s (non-tty) - pass --yes'%(why or 'destructive op'))
    if not _yn(msg):return False
    return True
def dry_only(o,msg,why=None):
    if not o.get('dry-run'):return
    _w=why or msg
    if is_json(o):out_json({'dry_run':True,'action':_w})
    else:sys.stdout.write('dry-run: %s - nothing was changed\n'%msg)
    sys.exit(0)
def need_arg(o,msg='missing argument'):
    if not o.get('_') or not o['_'][0]:die(2,msg)
    return o['_'][0]
def _int(v,dflt,what):
    if v in(None,'') :v=dflt
    try:return int(v)
    except (TypeError,ValueError):die(2,'%s must be an integer, got %r'%(what,v))
def sdk(c=None):return sdk_conf(c)
_TPLBLANK=[0]
def sb_from_raw(r,regs,suppress=None):
    m=(r.get('metadata')or{});c={k[4:]:v for k,v in m.items() if k.startswith('csb.')}
    if isinstance(m.get('csb'),dict):c.update(m['csb'])
    e=regs.get(r.get('sandboxID'))or{};tpl=e.get('tpl')or r.get('templateID')
    if not r.get('templateID')and not e.get('tpl'):_TPLBLANK[0]+=1
    _seed=next((d[k] for d in(c,m)for k in('label','name','hostname','app')if d.get(k)),None)
    return{'id':r.get('sandboxID'),'state':r.get('state'),'tpl':tpl,
           'label':e.get('label')or(None if suppress and tpl in suppress else _seed),'family':e.get('family')or c.get('family'),
           'kind':e.get('kind')or c.get('kind'),'parent':e.get('parent')or c.get('parent'),
           'ancestor':e.get('ancestor')or None,
           'nseq':(e.get('nseq') if e and 'nseq' in e else c.get('nseq')),
           'vols':[(x.get('name')if isinstance(x,dict)else str(x))for x in(r.get('volumeMounts')or[])if x]or None,
           'ts':e.get('ts')or c.get('ts')or r.get('startedAt'),'meta':m}
SEED_KEYS=('csb.label','name','label','hostname','app')
def seed_name(m):
    for k in SEED_KEYS:
        v=(m or{}).get(k)
        if isinstance(v,str)and v.strip():return k,v.strip()
    return None,None
_AUTOADOPT=[]
_AUTOPEND=[]
_ROMODE=[None]
_WIPED=[None]
def _wiped_warn(c):
    if reg(c)['entries']:return''
    if os.path.exists((c.get('reg')or'')+'.empty'):return''
    if os.path.exists(c.get('reg')or''):return''
    d=os.path.dirname(os.path.abspath(c.get('reg')or'.'));n=0;baks=[]
    try:
        a=c.get('aud')
        if a and os.path.exists(a):n=sum(1 for _ in open(a,encoding='utf-8',errors='replace'))
    except Exception:n=0
    try:baks=sorted(x for x in os.listdir(d)if'.bak-' in x)
    except Exception:baks=[]
    if not n and not baks:return''
    out='ledger is empty though this home was used (%s)%s'%(
        ('%d audit line(s)'%n)if n else'no audit trail left',
        (', %d backup(s)'%len(baks))if baks else'')
    if baks:out+=' - restore:  cp %s %s'%(os.path.join(d,baks[-1]),c.get('reg'))
    return out
def auto_adopt(c,sbs=None):
    if _sw('auto_no_adopt'):return[]
    E=reg(c)['entries']
    sbs=sbs if sbs is not None else fetch_sbs(c)
    if not sbs:return[]
    sbs=sorted(sbs,key=lambda s:(s.get('ts')or''))
    tal={t['id']:t['alias']for t in tpl_rows(c)if t.get('alias')}
    made=[]
    for s in sbs:
        if s['id'] in E:continue
        sk,sv=seed_name(s.get('meta'))
        own=s.get('label')
        if own and not sv:sk,sv='csb.label',own
        fam=s.get('family')or DATE_TPL.sub('',tal.get(s.get('tpl'))or'')or''
        if not fam or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}',fam):continue
        mint=not(sv and not label_err(sv,fam,E))
        ns=nseq_next(E,reg(c)['family_highwater'],fam)if mint else None
        lab=label_default(fam,ns)if mint else sv
        if label_err(lab,fam,E):lab=label_default(fam,ns)
        if mint:reg(c)['family_highwater'][fam]=max(reg(c)['family_highwater'].get(fam,0),ns)
        E[s['id']]={'label':lab,'family':fam,'kind':'start','parent':fam,'nseq':ns,
                    'tpl':s.get('tpl')or'',
                    'ts':s.get('ts')or _now(),'adopted':True,'auto':True,'seed':sk}
        made.append({'sandbox_id':s['id'],'label':lab,'seed':sk})
    if made:
        _AUTOADOPT[:]=_autoseen(c,made);_AUTOPEND[:]=[x['sandbox_id']for x in _AUTOADOPT];save_reg(c)
    return made
def auto_adopt_undo(c,pending_only=False):
    E=reg(c)['entries'];dead=[k for k in _AUTOPEND if k in E]if pending_only else[k for k,v in E.items()if(v or{}).get('auto')]
    for k in dead:
        del E[k];_REG_DEL.add(k)
    if dead:
        _AUTOPEND[:]=[x for x in _AUTOPEND if x not in set(dead)];save_reg(c)
    return dead
def _sb_mod():
    import cubesandbox as m
    return m
_CSB_SDK=None
_TPL_SDK=None
def _Sandbox():
    global _CSB_SDK
    if _CSB_SDK is None:_CSB_SDK=_sb_mod().Sandbox
    return _CSB_SDK
def _Template():
    global _TPL_SDK
    if _TPL_SDK is None:_TPL_SDK=_sb_mod().Template
    return _TPL_SDK
_ORIGC=[0.0,None]
SB_PG=100
SB_PGMAX=50
def _sb_list(c):
    import requests
    from urllib.parse import quote
    items=[];tok=None
    for _ in range(SB_PGMAX):
        try:
            r=requests.get(c['api']+'/v2/sandboxes?limit=%d'%SB_PG+('&nextToken=%s'%quote(tok)if tok else''),headers=_auth_hdrs(c),timeout=_http_secs())
            r.raise_for_status();body=r.json()
        except Exception as e:return None,False,'the sandbox list could not be read (%s)'%e
        if not isinstance(body,list):return None,False,'the sandbox list answered %s, not a list'%type(body).__name__
        page=[x for x in body if isinstance(x,dict)]
        items+=page
        nxt=(r.headers.get('x-next-token')or'').strip()or None
        if not nxt:return items,True,None
        if nxt==tok:return items,False,'the sandbox list handed back the same cursor twice'
        tok=nxt
    return items,False,'the sandbox list was still paging after %d pages'%SB_PGMAX
AUTOHIDE_MAX=2
AH_ROWS=5
def ah_ask():
    return _sw('auto_hide_ask')
def ah_hide():
    return ah_ask()or _sw('auto_hide')
_AHSK=[False]
_AHQ=[None]
_AHOK=[set()]
_AHSEEN=[frozenset()]
_AHHID=[0]
_SBW=[False]
_CMDN=[None]
_LISTISH=('ls','tree','snaps','clean')
def _listish():
    return _CMDN[0] is None or _CMDN[0] in _LISTISH
def _sb_partial(why):
    if _SBW[0] or not _listish():return
    _SBW[0]=True
    err('warning: incomplete list (%s) - auto-hide skipped'%(why or 'the server list was incomplete'))
def srv_origins(c):
    import time as _t
    if _ORIGC[1] is not None and _t.time()-_ORIGC[0]<5:return _ORIGC[1]
    try:
        got=set(fetch_snap_origins(c).values())
    except Exception:return _ORIGC[1] or set()
    _ORIGC[1]=got;_ORIGC[0]=_t.time()
    return got
def _autohide(c,alive):
    _merge_cur(led(c),led_read((c or cfg())['led']),_LED_DEL,_sec((c or cfg())['led'],'led'))
    e=reg(c)['entries'];gone=[g for g in e if g not in alive]
    if not gone:return
    mode,rows=_TUI.tui_autohide_plan(gone,e,_AHSK[0],_AHOK[0],_AHSEEN[0])
    if mode=='keep':return
    if mode=='ask':
        if _listish():_AHQ[0]=dict(gone=gone,rows=rows,total=len(e))
        return
    _sr=srv_origins(c)
    dirty=False;hid=0
    for g in gone:
        pv=e[g]
        if pv.get('seen'):continue
        if pv.get('kind')in('start','clone')and pv.get('label')and pv.get('family'):
            for cid,cv in e.items():
                if cid in alive and cv.get('kind')=='clone'and cv.get('parent')==pv['label']and not cv.get('ancestor'):
                    cv['ancestor']=pv['family'];dirty=True
        if any((v or {}).get('origin')==g for v in led(c).values()) or g in _sr:continue
        if not ah_hide():continue
        del e[g];_REG_DEL.add(g);dirty=True;hid+=1
    if dirty:save_reg(c)
    if hid:_AHHID[0]=hid
def seen_mark(c=None,sbs=None,snaporig=None):
    if _sw('auto_no_seen'):return[]
    c=c or cfg()
    if sbs is None:sbs=fetch_sbs(c)
    if snaporig is None:
        try:snaporig=fetch_snap_origins(c)
        except Exception:snaporig={}
    org={v for v in(snaporig or {}).values()if v}
    e=reg(c)['entries'];made=[]
    for s in sbs or[]:
        sid=s.get('id')
        if not sid or sid in e or not s.get('label'):continue
        if sid not in org:continue
        e[sid]={'label':s['label'],'family':s.get('family')or'','ts':s.get('ts'),'seen':True}
        made.append(sid)
    if made:save_reg(c)
    _seen_sweep(c,sbs,snaporig)
    return made
def _seen_sweep(c,sbs,snaporig):
    e=reg(c)['entries'];alive={s.get('id')for s in(sbs or[])};org={v for v in(snaporig or{}).values()if v};L=led(c)
    drop=[]
    for sid,r in list(e.items()):
        r=r or{}
        if not(r.get('seen')or r.get('killed')):continue
        if sid in alive or sid in org:continue
        if any((v or{}).get('origin')==sid for v in L.values()):continue
        _lab=r.get('label')
        if _lab and any(k!=sid and(v or{}).get('kind')=='clone'and(v or{}).get('parent')==_lab for k,v in e.items()):continue
        del e[sid];_REG_DEL.add(sid);drop.append(sid)
    if drop:save_reg(c)
    return drop
def _snap_orgs(c):
    try:_sl,_ok,_w=_snap_list(c)
    except Exception:return{}
    out={}
    for x in(_sl or[]):
        if not isinstance(x,dict):continue
        _i=x.get('snapshotID')or x.get('snapshot_id')
        _o=x.get('originSandboxID')or x.get('origin')
        if _i and _o:out[_i]=_o
    return out
def _seen_gc(c,delsnaps,orgs):
    e=reg(c)['entries'];dropped=[];_d=set(delsnaps)
    for sid in _d:
        o=(orgs or {}).get(sid)
        if not o or o not in e:continue
        _r=e[o] or {}
        if not(_r.get('seen') or _r.get('killed')):continue
        if any(v==o for k,v in(orgs or {}).items()if k not in _d):continue
        if any((v or {}).get('origin')==o for v in led(c).values()):continue
        _lab=_r.get('label')
        if _lab and any(k!=o and (v or {}).get('kind')=='clone' and (v or {}).get('parent')==_lab for k,v in e.items()):continue
        del e[o];_REG_DEL.add(o);dropped.append(o)
    if dropped:save_reg(c)
    return dropped
def fetch_sbs(c=None):
    c=c or cfg()
    raw,full,why=_sb_list(c)
    if raw is None:
        try:raw=_Sandbox().list_v2(config=sdk(c))
        except Exception as ex:die(3,'list_v2 failed: %s'%ex)
        full,why=False,why or 'the SDK list was used instead of the paged one'
    try:_SB_FULL[0]={r.get('sandboxID')for r in raw}if full else None
    except Exception:_SB_FULL[0]=None
    if full:_autohide(c,{r.get('sandboxID')for r in raw})
    else:_sb_partial(why)
    regs=reg(c)['entries']
    _sup={tid for tid,m in (reg(c).get('templates')or{}).items() if isinstance(m,dict)and(m.get('local_labels')or m.get('alias'))}
    return[sb_from_raw(r,regs,_sup) for r in raw]
def fetch_tpls(c=None):
    c=c or cfg()
    try:return _Template().list(config=sdk(c))
    except Exception as ex:die(3,'Template.list failed: %s'%ex)
def tpl_rows(c=None):
    out=[]
    for t in fetch_tpls(c):
        out.append({'id':t.template_id,'alias':t.name or None,'status':t.status,'ts':t.created_at,'is_snap':t.template_id.startswith('snap-')})
    try:
        _it,_ok,_w=_snap_list(c or cfg())
    except Exception:_it=None
    for _s in(_it or[]):
        if not isinstance(_s,dict):continue
        _i=_s.get('snapshot_id')or _s.get('snapshotID')or _s.get('id')or _s.get('snapshotId')
        if not _i or any(r['id']==_i for r in out):continue
        _n=(_s.get('names')or[None])[0]
        out.append({'id':_i,'alias':_n,'status':_s.get('status')or'READY','ts':_s.get('ts'),
                    'is_snap':True,'family':_s.get('family')})
    try:_lt=reg(c or cfg()).get('templates',{})or{}
    except Exception:_lt={}
    for _i,_r in _lt.items():
        if any(r['id']==_i for r in out):continue
        out.append({'id':_i,'alias':(_r or {}).get('alias')or (_r or {}).get('name')or None,
                    'status':'DELETED','ts':(_r or {}).get('ts'),'is_snap':False,'deleted':True})
    return out
def _ot_check(ot):
    if ot is not None and ot not in('kill','pause'):die(2,'--on-timeout accepts kill or pause (got %r)\n              example: --on-timeout pause'%ot)
    return ot or'pause'
def _meta(fam,kind,parent,label,nseq):
    f=fam or '';p=parent or ''
    return{'csb.family':f,'csb.kind':kind,'csb.parent':p,'csb.label':label,'csb.nseq':str(nseq),'csb.ts':_now()}
def _find_sb(arg,c):
    sbs=_val({'o':'json'}if _JSONMODE[0] else{},'reading the sandboxes',lambda:fetch_sbs(c));cand=resolve(arg,[{'id':s['id'],'label':s['label'] or '', 'family':s['family'] or ''} for s in sbs])
    if not cand:return None,None
    exact=[h for h in cand if h['id']==arg]
    if len(cand)>1 and not exact:
        if is_tty():
            for i,h in enumerate(cand,1):print('%2d) %s %s'%(i,h.get('label')or h['id'][:8],h['id']))
            try:r=input('ambiguous label "%s": pick 1-%d> '%(arg,len(cand)))
            except EOFError:die(1,'cancelled')
            if not r.isdigit()or not 1<=int(r)<=len(cand):die(1,'cancelled')
            h=cand[int(r)-1]
        else:die(2,'ambiguous label %s: %s (pass a full sandbox id)'%(arg,','.join(sorted(h['id'] for h in cand))))
    else:h=(exact or cand)[0]
    return next(s for s in sbs if s['id']==h['id']),sbs
def cmd_ls(o,c):
    _TPLBLANK[0]=0
    sbs,tps=_val(o,'reading the sandboxes',lambda:(fetch_sbs(c),tpl_rows(c)))
    try:_sbx_sweep(c,_SB_FULL[0])
    except Exception as _e:_swallow('sbx sweep',_e)
    regs=reg(c)['entries']
    tal={t['id']:t['alias']for t in tps if t['alias']}
    def tn(s):
        a=tal.get(s.get('tpl'))
        return a or(short_id(s['tpl'])+_ELT if s.get('tpl')else'')
    live=[{'sandbox_id':s['id'],'label':s['label'] or'(no name)','state':s['state'],'template':s['tpl'] or'', 'template_alias':tn(s),'family':s['family'] or'','source':s.get('kind') or'-','ts':s.get('ts') or'-'} for s in sbs]
    live.sort(key=lambda x:_tkey(x['ts']),reverse=True)
    if not is_json(o):
        hdr=['LABEL','SOURCE','STATE','TEMPLATE','ID','TS']
        rows=[[x['label'],x['source'],x['state'],x['template_alias']or x['template'],x['sandbox_id'][:8],_disp(x['ts'])] for x in live]
        if not rows:print('(no sandboxes here)  start one:  csb start <template>');return 0
        fmt(hdr,rows)
        if _TPLBLANK[0]:err('note: no template for %d sandbox(es) - shown from the local ledger.'%_TPLBLANK[0])
        _ent0=reg(c)['entries']
        _tprint('  short ids here; full ids: csb ls -o json')
        return 0
    _ent=reg(c)['entries']
    out=[{k:x[k]for k in('sandbox_id','label','source','state','template','template_alias','family','ts')if k in x}for x in live]
    out_json(out);return 0
def cmd_tz(o,c):
    if o.get('_'):die(2,'tz takes no arguments - set the TZ env var instead.')
    c=c or cfg();sk=_skew(c);r=reg(c);off=_tzoff();_P=prefs(c)
    ent=r.get('entries')or{};lg=led(c)
    old=sum(1 for v in list(ent.values())+list(lg.values())if not str((v or{}).get('ts')or'').endswith('Z'))
    raw=_rawnow().strftime('%Y-%m-%dT%H:%M:%SZ')
    fix=0 if sk is None else(0 if abs(sk)<=5 else -sk)
    al='this machine clock'if not fix else'server-aligned (written timestamps get %+ds)'%fix
    if is_json(o):
        out_json({'local_zone':time.strftime('%Z')or'?','local_offset':off,'local_now':_disp(raw),'utc_now':raw,
                  'server_skew_s':sk,'clock_correction_s':fix,'ts_writes':al,
                  'ledger_tzoff':_P.get('tzoff')or'','ts_format':'UTC ISO-8601 (Z suffix)',
                  'config_file':prefs_path(c),
                  'legacy_local_timestamps':old});return 0
    print('%-14s %s  (%s)'%('LOCAL ZONE',time.strftime('%Z')or'?',off))
    print('%-14s %s'%('LOCAL NOW',_disp(raw)))
    print('%-14s %s'%('UTC NOW',raw))
    print('%-14s %s'%('SERVER CLOCK','unreachable'if sk is None else('%+ds  (%s)'%(sk,'ok'if abs(sk)<=300 else'DIFFERS from this machine'))))
    print('%-14s %s'%('TS WRITES',al))
    print('%-14s %s'%('LEDGER TZOFF',_P.get('tzoff')or'(none recorded)'))
    print('%-14s %s'%('CONFIG FILE',prefs_path(c)))
    print('%-14s %s'%('TS FORMAT','UTC ISO-8601 (Z suffix)'))
    if _P.get('tzoff')and _P.get('tzoff')!=off:
        err('note: ledger tzoff %s != this machine %s (written on another machine); timestamps are UTC, only display differs.'%(_P.get('tzoff'),off))
    if old:print('%-14s %d entry(ies) old format - use the tzoff.'%('LEGACY',old))
    if sk is not None and abs(sk)>300:
        print('WARN: clock is %+ds off - fix it; timestamps are corrected.'%sk)
    return 0
_LB=re.compile(r'[\x0a-\x0d]')
_C0=re.compile(r'[\x00-\x1f\x7f]')
_ANSI=re.compile(r'\x1b\[[0-9;?]*[A-Za-z]|\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)')

def _cln(s):
    return _C0.sub('',_LB.sub(' ',_ANSI.sub('',str(s)).replace('\t',' '*4)))

def _dw(s):
    return sum(2 if unicodedata.east_asian_width(c)in'WF'else 1 for c in str(s))
def _fitw(s,w):
    s=_C0.sub('',_LB.sub(' ',str(s)))
    if _dw(s)<=w:return s+' '*(w-_dw(s))
    _e=_ELT if w>=_dw(_ELT)else(_ELT[:max(0,w)]if _ASC else _ELT)
    o=''
    for c in s:
        if _dw(o)+_dw(c)>w-_dw(_e):break
        o+=c
    return o+_e+' '*max(0,w-_dw(o)-_dw(_e))
def _termw(dflt=100):
    if not sys.stdout.isatty():return None
    try:
        n=os.get_terminal_size().columns
        return n if n>=24 else dflt
    except Exception:return dflt
def _wrapw(s,w):
    s=_cln(s).rstrip()
    if w<8 or _dw(s)<=w:return[s]
    lead=re.match(r' *',s).group(0);body=s[len(lead):].strip()
    bw=max(8,w-_dw(lead))
    out=[];cur=''
    for word in body.split(' '):
        if not word:continue
        while _dw(word)>bw:
            take=''
            for ch in word:
                if _dw(take)+_dw(ch)>bw:break
                take+=ch
            if cur:out.append(cur);cur=''
            out.append(take);word=word[len(take):]
        if not cur:cur=word
        elif _dw(cur)+1+_dw(word)<=bw:cur+=' '+word
        else:out.append(cur);cur=word
    if cur:out.append(cur)
    return out or['']
def _foldlines(s,w):
    ls=_wrapw(s,w)
    lead=re.match(r' *',_cln(s)).group(0)
    return [lead+ls[0]]+[lead+x for x in ls[1:]]
def _tprint(line,hang='',W=-1):
    W=_termw()if W==-1 else W
    if not W or _dw(_cln(line))<=W:print(line);return
    ls=_wrapw(line,W)
    lead=re.match(r' *',_cln(line)).group(0)
    if not hang:hang=lead
    print(lead+ls[0])
    for x in ls[1:]:
        print((hang if _dw(hang)+_dw(x)<=W else'')+x)
def fmt(head,rows,width=None):
    if not rows:return
    W=width or _termw();n=len(head)
    w=[max(_dw(head[i]),max((_dw(r[i])for r in rows),default=0))for i in range(n)]
    while W and sum(w)+2*(n-1)>W:
        i=max(range(n),key=lambda j:w[j])
        if w[i]<=4:break
        w[i]-=1
    print('  '.join(_fitw(head[i],w[i])for i in range(n)).rstrip())
    print('  '.join('-'*w[i]for i in range(n)))
    for r in rows:print('  '.join(_fitw(r[i],w[i])for i in range(n)).rstrip())
def out_json(x):_json.dump(x,sys.stdout,ensure_ascii=False,indent=1);sys.stdout.write('\n')
def _snap_src(c,src):
    for _s in((_snap_list(c)[0])or[]):
        if not isinstance(_s,dict):continue
        _i=_s.get('snapshot_id')or _s.get('snapshotID')or _s.get('id')or _s.get('snapshotId')
        if not _i:continue
        if _i==src or src in(_s.get('names')or[]):return _i
    return None
def _snap_vol_warn(c,src):
    org=((snap_facts(c)[0]or{}).get(src)or{}).get('origin')or''
    if not org:return''
    raw,full,why=_sb_list(c)
    if raw is None:return''
    _r=reg(c)['entries']
    for x in raw:
        if x.get('sandboxID')!=org:continue
        vs=sb_from_raw(x,_r).get('vols')or[]
        if not vs:return''
        return('WARN: %s came from a sandbox that mounts a volume\n'
               '  volume    %s\n'
               '  the new sandbox mounts the SAME live volume, and a snapshot revives\n'
               '  the writer that was on it: two writers can corrupt the files\n'
               '  copy them out first:  csb cp <sandbox>:/data/dir ./\n'
               %(short_id(src),', '.join(vs[:2])+(' ...'if len(vs)>2 else'')))
    return''
SNAPNAME_OK=1
def cmd_start(o,c):
    src=need_arg(o,'start: <template|alias|snapshot_id>')
    tpls=tpl_rows(c);aliases={t['alias']:t['id'] for t in tpls if t['alias'] and not t['is_snap']}
    snapids=[t['id'] for t in tpls if t['is_snap']]
    _noalias=None
    _byid={t['id']:t for t in tpls}
    if src not in aliases and src in _byid and src not in snapids:
        if _byid[src].get('alias'):
            err('note: %s is a template id - using its alias %s'%(short_id(src),_byid[src]['alias']))
            src=_byid[src]['alias']
        else:
            die(2,'%s needs an alias\nfix   csb tpl alias %s <name>'%(short_id(src),src))
    tled=reg(c).get('templates',{})
    fam=None
    if _noalias:fam=_noalias
    is_commit=bool(re.match(r'^(.*)-commit-\d{8}(-\d+)?$',src))
    if src in aliases:
        fam=start_family(src,tled.get(aliases[src]) or {})
        _tl=tled.get(aliases[src]) or {}
        if _tl.get('family')!=src:
            _tl['family']=src
            try:reg(c)['templates'][aliases[src]]=_tl;save_reg(c)
            except Exception:_swallow('family refresh',None)
    if src not in aliases and src not in _byid and src not in snapids:
        _hit=_snap_src(c,src)
        if _hit and(_hit==src or SNAPNAME_OK):snapids=snapids+[_hit];src=_hit
    if SNAPNAME_OK and src not in aliases and src not in _byid and src not in snapids:
        _sn=next((k for k,v in led(c).items()if(v.get('name')or'')==src),None)
        if _sn in snapids:src=_sn
        elif _sn:
            _live=_snap_src(c,src)
            if _live:snapids=snapids+[_live];src=_live
            else:snapids=snapids+[_sn];src=_sn
    is_snap_src=src in snapids
    if not is_snap_src:
        if src not in aliases and src not in _byid:
            _hint=('  no template or snapshot has this id - run  csb tpl ls\n'
                   '  (left column = alias, right column = id)')if str(src).startswith('tpl-')else(
                   '  no template alias and no snapshot name matches - run  csb tpl ls  or  csb snaps')
            die(2,'unknown template: %s\nfix   csb tpl ls lists the templates'%src)
    else:
        ld=led(c);e=ld.get(src) or {}
        fam=e.get('fam')
        if not fam:
            fam=o.get('family')
            if not fam and not o.get('label'):
                die(3,'snapshot has no family\nfix   csb start %s --family <alias> --label <name>'%src)
    _srcfam=fam
    fam=naming_fam(fam,is_snap_src,o.get('label'),o.get('family'))
    if is_snap_src and not fam and not is_json(o):
        err('%s is not <family>_<NN>, so it is recorded family-less - add --family <root-alias>.'%o['label'])
    if o.get('family')and not is_snap_src and o['family']!=fam:
        err('note: --family %s ignored - a sandbox started from a template stays in that template family (%s)'%(o['family'],fam))
    n=_int(o.get('n'),1,'--n');cc=_int(o.get('concurrency'),1,'--concurrency')
    if n<1:die(2,'--n must be >= 1 (got %d)\n    omit --n when you only need one sandbox'%n)
    if cc<1:die(2,'--concurrency must be >=1, got %d'%cc)
    if _m(o,'vol') and is_snap_src:
        die(2,'start --vol with a snapshot source is not supported: snapshots carry their own mounts (400/130400)\nfix   drop --vol, or start from a template')
    if _m(o,'vol') and not _sw('dev_panel'):vol_warn(err if is_json(o) else print)
    if is_snap_src and not _sw('dev_panel'):
        _vw=_snap_vol_warn(c,src)
        if _vw:err(_vw)
    entries=reg(c)['entries'];hw=reg(c)['family_highwater']
    _nsp,_nsk=(fam or src),(fam or src)
    if not o.get('label') and not is_snap_src:
        try:_nsp,_nsk=ns_for(c,src)
        except Exception:_nsp,_nsk=(fam or src),(fam or src)
    jobs=[]
    if o.get('label'):
        if isinstance(o['label'],list):die(2,'--label repeated - pick one (got %s)'%', '.join(map(str,o['label'])))
        _known={k:enreg(v) for k,v in entries.items()}
        for lab in bulk_labels(o['label'],n):
          errl=label_err(lab,fam,_known)
          if errl:
            if errl=='collision':
                _live={x.get('id')for x in fetch_sbs(c)}
                _hold=[k for k,e2 in list(entries.items())if enreg(e2).get('label')==lab]
                _run=[k for k in _hold if k in _live]
                _dead=[k for k in _hold if k not in _live]
                if _run:
                    die(2,'label %s: already used by a running sandbox %s\n  fix   csb kill %s --yes%s   (or rename)'%(
                        lab,_run[0][:8],_run[0],
                        '\n      (a killed sandbox with this label is also still in the ledger - csb clean %s clears it)'%_dead[0]
                        if _dead else ''))
                die(2,'label %s: collision%s - drop the dead node:  csb clean %s'%(
                    lab,' (the old sandbox is gone - only the local ledger still holds it)'if _dead else'',_dead[0]))
            if errl=='bad charset/length':
                die(2,'label %r: bad charset/length (letters, digits, _-, <=64; e.g. zoo-01)'%lab)
            die(2,'label %s: %s'%(lab,errl))
        jobs=[(lab,0)for lab in bulk_labels(o['label'],n)]
    envs=dict(_kv(x,'--env') for x in _m(o,'env'))
    _inh=not any(o.get(k)is not None for k in('net','no-net','allow-out','proxy','no-dns','allow-dns','dns-server'))
    _pv=(str(o.get('proxy')or'')).strip()
    _mode=net_mode(o,prefs(c).get('net_choice') or'on')
    if _mode=='template':_mode='on'
    _ao_raw=_allow_out(o)
    if _ao_raw is not None:_ao_raw=_norm_allow(_ao_raw)
    _dns_on=(not _inh) and not bool(o.get('no-dns')) and bool(_ao_raw) and '0.0.0.0/0' not in (_ao_raw or [])
    if not _inh and o.get('allow-dns'):
        sys.stderr.write('csb: --allow-dns is now the default for a whitelist (use --no-dns to turn DNS off)\n')
    if not _inh and o.get('no-dns') and _ao_raw and any(not _ao_is_cidr(x) for x in _ao_raw):sys.stderr.write('csb: domains imply DNS - the platform resolves them; --no-dns will not block that\n')
    if not _inh and o.get('no-dns') and not _ao_raw:
        sys.stderr.write('csb: --no-dns has no effect without an --allow-out list - ignored\n');_dns_on=False
    if not _inh and o.get('dns-server') and not _dns_on:
        sys.stderr.write('csb: --dns-server needs a whitelist and no --no-dns - ignored\n')
    if o.get('dns-server') and _dns_on:
        _dsv=str(o.get('dns-server')).strip()
        try:
            import ipaddress as _ipa;_ipa.ip_address(_dsv)
        except Exception:die(2,'--dns-server: not an IP address: %s\nfix   --dns-server 119.29.29.29'%_dsv)
    if not _inh and _mode=='off' and (_dns_on or o.get('dns-server')):
        sys.stderr.write('csb: --net off - --allow-dns / --dns-server ignored for this sandbox\n');_dns_on=False
    if not _inh and _dns_on and _ao_raw and o.get('async'):
        sys.stderr.write('csb: --async - DNS is not added for this start; run without --async to allow the resolver\n')
    if not _inh and o.get('net')is not None and _mode=='on' and _ao_raw is None and not _pv:
        die(2,'--net on needs --allow-out <cidr|domain>[, ...] (or --proxy <url>), '
               'see `csb help` - nothing is applied from memory any more')
    if _mode=='off' and (o.get('allow-out')is not None or o.get('proxy') is not None):
        sys.stderr.write('csb: --net off - --allow-out / --proxy ignored for this sandbox\n')
    _auto_pe=_auto_proxy_env(o)if _mode!='off'else{}
    if _auto_pe and not any(str(k).lower()in('http_proxy','https_proxy','all_proxy')for k in envs):
        envs={**_auto_pe,**envs}
    _pol=_net_pol(_auto_pe,_ao_raw,o,_mode)
    if not _inh and _mode=='on' and _ao_raw is not None and not _ao_raw:
        _pol=['0.0.0.0/0']
    for _mx in _m(o,'meta'):_kv(_mx,'--meta')
    kind='from-snap' if is_snap_src else 'start'
    ot=_ot_check(o.get('on-timeout'))
    tm=_tmo(o,2592000)
    kwb=dict(template=src,timeout=tm,lifecycle={'on_timeout':ot})
    if not _inh:
        if _mode=='off':kwb['allow_internet_access']=False
        if _pol:
            _nw={'allow_out':_pol,'allow_internet_access':True}
            _dn=_net_deny(_ao_raw)
            if _dn:_nw['deny_out']=_dn
            elif not _ao_raw and '0.0.0.0/0' in _pol:_nw['deny_out']=[]
            kwb['network']=_nw
        elif envs:kwb['env_vars']=envs
    elif envs:kwb['env_vars']=envs
    if o.get('no-net'):kwb['allow_internet_access']=False
    vms=None
    if _m(o,'vol'):
        import cubesandbox as cb
        _vpl,_bad=vol_plan(_m(o,'vol'),vol_known(c))
        if _bad:die(2,_bad[1])
        vms={p:cb.VolumeMount(cb.Volume(i,v),read_only=ro)for p,v,i,ro in _vpl}
        kwb['volume_mounts']=vms
    dry_only(o,'start %s from %s'%(_pl(n,'sandbox','sandboxes'),src),why='starting %d sandboxes'%n)
    if o.get('proxy')is not None:
        try:proxy_set(c,_pv)
        except Exception as _e:_swallow('proxy save',_e)
    if _mode!='off' and _ao_raw is not None and not _inh:allow_out_set(c,_ao_raw)
    if n>20 and not confirm(o,'start %d sandboxes? (bulk > 20: double-check)'%n,why='starting %d sandboxes'%n):return 1
    if not o.get('label'):jobs=_reserve_labels(c,_nsp,n,_nsk)
    made=[]
    try:
        def mk(j):
            lab0,ns0=j
            meta=_meta(fam,kind,src if is_snap_src else fam,lab0,ns0)
            for x in _m(o,'meta'):
                k,v=_kv(x,'--meta');meta[k]=v
            kw=dict(kwb,metadata=meta)
            if vms is not None:kw['volume_mounts']=vms
            nsb=_Sandbox().create(**kw)
            _save_sbxenv(c,nsb.sandbox_id,envs if _pol else{},('template'if _inh else _mode),_pol,_net_deny(_ao_raw))
            if _dns_on and _ao_raw and not o.get('async'):
                _srv=[]
                try:
                    _cr=nsb.commands.run('cat /etc/resolv.conf',timeout=10)
                    _srv=resolv_servers(getattr(_cr,'stdout','')or'')
                except Exception as _e:_swallow('dns read',_e)
                _ov=str(o.get('dns-server')or os.environ.get('CSB_DNS')or'').strip()
                if _ov:_srv.append(_ov)
                _srv=list(dict.fromkeys(_srv))
                if not _srv:sys.stderr.write('csb: DNS not added - could not read the resolver; pass --dns-server <ip>\n')
                else:
                    _newpol=list(dict.fromkeys(list(_pol)+[x for x in (dns_cidr(v) for v in _srv) if x]))
                    try:nsb.update_network({'allow_out':_newpol,'deny_out':['0.0.0.0/0'],'allow_internet_access':True})
                    except Exception as _e:sys.stderr.write('csb: DNS not added: %s\n'%_e)
                    else:_save_sbxenv(c,nsb.sandbox_id,envs if _pol else{},('template'if _inh else _mode),_newpol,['0.0.0.0/0'],_srv)
            return nsb.sandbox_id,lab0,ns0,_svts(nsb._data)
        if cc>1 and n>1:
            from concurrent.futures import ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=min(cc,n)) as ex:res=list(ex.map(mk,jobs))
        else:res=[mk(j) for j in jobs]
        for sid0,lab0,ns0,ts0 in res:
            entries[sid0]={'label':lab0,'family':fam,'nseq':ns0,'kind':kind,'parent':src if is_snap_src else fam,'ancestor':(_srcfam or fam)if is_snap_src else fam,'template_id':src,'ts':ts0 or _now()}
            made.append({'sandbox_id':sid0,'label':lab0})
        if made:save_reg(c)
        if _mode!='off' and not _inh:egress_last_save(c,_mode,_ao_raw,_dns_on,_pv)
        sv=_val(o,'',lambda:_srv_started(c,{x[0]for x in res}))
        for sid0,lab0,ns0,ts0 in res:
            if sv.get(sid0):entries[sid0]['ts']=sv[sid0]
    except Exception as ex:
        _doc=len(made)
        for sid0 in [x['sandbox_id'] for x in made]:
            entries.pop(sid0,None)
            try:_Sandbox().connect(sid0,timeout=_connect_secs(),config=sdk(c)).kill()
            except Exception as _e:_swallow('meta',_e)
        if made:save_reg(c)
        _wy=_why_server(ex)
        die(3,'start failed at %d of %s: %s (rolled back, nothing left)%s'%(_doc,_pl(n,'sandbox','sandboxes'),_wy,_cap_hint(_wy)),raw=str(ex))
    save_reg(c)
    if not o.get('async'):
        if not is_json(o):err('starting %s from %s'%(_pl(n,'sandbox','sandboxes'),src))
        _wt=_wait_guard(o)
        try:
            for sid0 in [x['sandbox_id'] for x in made]:
                if _wait_state(sid0,'running',o,c)=='stop':
                    if not is_json(o):err('stopped watching - the rest keep starting on the platform (csb ls shows them)')
                    break
        finally:_wait_restore(_wt)
    if not is_json(o)and n>1:err('started %d of %s from %s'%(len(made),_pl(n,'sandbox','sandboxes'),src))
    labs={x['label'] for x in made}
    ids={x['sandbox_id'] for x in made}
    _srv=fetch_sbs(c)
    try:_sbx_sweep(c,_SB_FULL[0])
    except Exception as _e:_swallow('sbx sweep',_e)
    dup=[s for s in _srv if s.get('label') in labs and s['id'] not in ids]
    _ws=[_dupwarn(dup)]if dup else[]
    _pm={s.get('id'):((s.get('meta')or{}).get('csb.label'))for s in(_srv or[])}
    _chg=False
    for _m0 in made:
        _pl0=_pm.get(_m0['sandbox_id'])
        if _pl0 and _pl0!=_m0['label']:
            _e0=entries.setdefault(_m0['sandbox_id'],{})
    if _chg:save_reg(c)
    w='\n'.join(_ws)if _ws else None
    if is_json(o):
        d={'made':[{'sandbox_id':x['sandbox_id'],'label':x['label'],'state':'running'} for x in made]} if n>1 else {'sandbox_id':made[0]['sandbox_id'],'label':made[0]['label'],'state':'running'}
        if w:d['warning']=w
        out_json(d)
    else:
        if w:err(w)
        _wd='requested (--async, not waited)'if o.get('async')else'started'
        for x in made:_okl(_wd,x['sandbox_id'],x['label'])
    return 0
def _dupwarn(dup,limit=3):
    d=sorted({(s.get('label')or'',s.get('id')or'')for s in dup})
    head='  '.join('%s #%s'%(l,short_id(i))for l,i in d[:limit])+('  ... and %d more'%(len(d)-limit)if len(d)>limit else'')
    return('WARN: this name is taken on the cluster: %s\n'
           '  a label is unique only inside one ledger - another ledger or the WebUI can hold it too,\n'
           '  so two nodes can share it: use the #id to tell them apart (csb tree shows both)'%head)
def _stale_meta_warn(made,sbs):
    got={s.get('id'):((s.get('meta')or{}).get('csb.label'))for s in(sbs or[])}
    bad=[(m.get('label'),got.get(m.get('sandbox_id')))for m in made
         if got.get(m.get('sandbox_id'))and got.get(m.get('sandbox_id'))!=m.get('label')]
    if not bad:return''
    head='  '.join('ledger %s -> platform %s'%(a,b)for a,b in bad[:3])+('  ... and %d more'%(len(bad)-3)if len(bad)>3 else'')
    return('WARN: the platform kept the source label (template or snapshot): %s\n'
           '  why   a sandbox started from a template or snapshot inherits its metadata; the create request cannot\n'
           '        override a key the source already has (probe: a fresh key is merged, csb.label is not)\n'
           '  csb   the ledger keeps the new label, so csb ls / csb tree are right\n'
           '  risk  WebUI and the v2 API show the inherited one - the platform has to let the request win'%head)

def enreg(e):return{'family':e.get('family'),'label':e.get('label'),'nseq':e.get('nseq')}
def _kv(x,what):
    if not isinstance(x,str)or'=' not in x:die(2,'%s needs KEY=VALUE (got %r)\n      example: --env FOO=1'%(what,x))
    k,v=x.split('=',1)
    if not k:die(2,'%s: empty key (got %r; e.g. FOO=1)'%(what,x))
    return [k,v]
def _m(o,k):
    v=o.get(k)
    if v is None:return[]
    return v if isinstance(v,list) else [v]
def _inst(sb,c):
    return _Sandbox().connect(sb['id'],timeout=_connect_secs(),config=sdk(c))
def _raw(sb,c):
    return _Sandbox()({'sandboxID':sb['id'],'templateID':sb.get('tpl')or''},config=sdk(c))
def _label2entry(label,entries):
    return next((k for k,v in entries.items() if v.get('label')==label),None)
def _del_entry(sid,c):
    if sid in reg(c)['entries']:del reg(c)['entries'][sid];_REG_DEL.add(sid);save_reg(c)
    _sbx_drop(c,sid)
def _autoclone_snap(c,sid,o):
    import time as _t
    ent=reg(c)['entries'].get(sid)
    if not ent or ent.get('kind')!='clone':return
    snap=ent.get('template_id')
    if not snap or not snap.startswith('snap-'):return
    others=[k for k,v in reg(c)['entries'].items()if k!=sid and v.get('kind')=='clone' and v.get('template_id')==snap]
    if others:
        try:
            if any(x['id'] in others for x in fetch_sbs(c)):return
        except Exception:return
    if not is_json(o):
        err('temp snapshot %s kept'%short_id(snap))
        err('fix   csb snaprm %s --yes'%snap)
def cmd_kill(o,c):
    label=need_arg(o,'kill: <id>');sb,_=_find_sb(label,c)
    sid=None;gone=False
    if sb:sid=sb['id']
    else:
        sid=_label2entry(label,reg(c)['entries'])
        if not sid:
            if is_json(o):out_json({'sandbox_id':None,'label':label,'state':'nomatch','ghost':False,'snapshots':0,'note':'no match on the server or in the ledger'});return 2
            die(2,'unknown sandbox: %s (see csb ls; full ids: csb ls -o json)%s'%(label,_idhint(c,label)))
        gone=True
    dsnap=[s0 for s0,e0 in led(c).items()if e0.get('origin')==sid]
    if sb and is_tty() and not is_json(o) and not o.get('yes') and not o.get('dry-run'):
        if dsnap:
            _who=label if label!=sid else short_id(sid)
            _ns=_pl(len(dsnap),'snapshot','snapshots')
            err('%s are NOT deleted - csb snaprm removes them, d clears the node'%_ns)
            if not _yn('kill it'):return 1
        elif not confirm(o,'kill sandbox %s? (irreversible)'%label,why='killing sandbox %s'%label):return 1
    elif o.get('dry-run') or not o.get('yes'):
        if not confirm(o,'kill sandbox %s? (irreversible)'%label,why='killing sandbox %s'%label):return 1
    if sb:
        try:_val(o,'killing %s'%label,lambda:_raw(sb,c).kill())
        except Exception as ex:
            if '404' in str(ex) or 'NotFound' in str(ex):gone=True
            else:die(3,'kill failed: %s'%ex)
    _autoclone_snap(c,sid,o)
    left=[s0 for s0,e0 in led(c).items()if e0.get('origin')==sid]
    if left:
        if not is_json(o):err('note: %d snapshot(s) remain - [D] node; d clears it after snaprm.'%len(left))
        _r=reg(c)['entries'].get(sid)
        if _r is not None and not _r.get('killed'):_r['killed']=_now();save_reg(c)
    else:_del_entry(sid,c)
    if is_json(o):out_json({'sandbox_id':sid,'label':label,'state':'gone' if gone else 'terminated','ghost':bool(left),'snapshots':len(left),'note':None})
    else:_okl('killed',sid,label)
    return 0
_INFO_GRP=(('IDENTITY',('sandbox_id','label','state','template','family','kind','parent','nseq','ts')),
           ('ENDPOINT',('port','url','domain')),
           ('RUNTIME',('started_at','end_at','runtime_snapshot')),
           ('RESOURCES',('cpu_count','cpu_milli','memory_mb','disk_size_mb','envd_version','client_id')),
           ('VOLUME',('vols',)),
           ('NETWORK',('net_mode','allow_out_applied','proxy_for_exec','dns')),
           ('NOTE',('note',)))
_INFO_FIX={'sandboxID':'sandbox_id','templateID':'template','startedAt':'started_at','endAt':'end_at','cpuCount':'cpu_count',
           'cpuMilli':'cpu_milli','memoryMB':'memory_mb','diskSizeMB':'disk_size_mb','envdVersion':'envd_version','clientID':'client_id'}
_INFO_TIP={'port':'envd - the in-sandbox API this url uses','nseq':"this label's creation counter",
           'ts':'when csb wrote it','cpu_milli':'millicores; cpu_count = this / 1000',
           'memory_mb':'MiB; the name is historical, not a unit',
           'disk_size_mb':'not a real size - this build always sends 0',
           'envd_version':'the agent build inside this sandbox','client_id':'the host that runs this sandbox',
           'end_at':'projected timeout'}
def _tip(k,v):
    t=_INFO_TIP.get(k)
    if not t or '('in str(v):return''
    if k=='disk_size_mb'and str(v).strip()not in('0','0.0'):return''
    return t
def _ident(sb):
    k=sb.get('kind')or'';p=sb.get('parent')or''
    if p and k=='start':p='%s  (the template it was started from)'%p
    return{'sandbox_id':sb['id'],'label':sb.get('label')or'(no name)','state':sb.get('state')or'',
           'template':sb.get('tpl')or'','family':sb.get('family')or'','kind':k,'parent':p,
           'nseq':sb.get('nseq'),'ts':sb.get('ts'),
           'vols':', '.join(sb.get('vols')or[])}
def _info_print(d,c=None,ident=None):
    d=dict(d or{});_m=d.pop('metadata',None);rows={}
    for k,v in(ident or{}).items():
        if v not in(None,''):rows[k]=_disp(v)if(k=='ts'or k.endswith('_at'))else v
    for k,v in d.items():
        if v in(None,''):continue
        kk=_INFO_FIX.get(k,k)
        if kk=='end_at'and str(v).strip()in('0','0.0'):rows[kk]='none  (paused - no countdown)';continue
        if kk=='disk_size_mb'and str(v).strip()in('0','0.0','0.00'):
            rows[kk]='n/a  (this build reports no disk size)';continue
        rows[kk]=_disp(v)if(kk=='ts'or kk.endswith('_at'))else v
    if isinstance(_m,dict):
        for k2,v2 in sorted(_m.items()):
            if v2 not in(None,''):rows['metadata.%s'%k2]=_hum(v2)
    elif _m not in(None,''):rows['metadata']=_m
    if rows.get('end_at')in(None,'')and rows.get('started_at'):rows['end_at']='none  (timeout -1: this sandbox never expires)'
    tv=str(rows.get('template')or'')
    if tv.startswith('tpl-')and c:
        try:
            al=next((t['alias']for t in tpl_rows(c)if t['id']==tv),None)
            if al:rows['template']='%s  (%s)'%(al,tv)
        except Exception:pass
    try:
        _sid=sb.get('id')if 'sb' in dir() else None
    except Exception:_sid=None
    _sid=_sid or rows.get('sandbox_id')
    if _sid:
      try:
        _rec0=sbx_net_saved(c,_sid)
        _nm0=_rec0 or sbx_net_mode(c,_sid)
        rows['net_mode']=(_nm0+('  (proxy env is added by exec/shell)'if _nm0!='off'and _proxy_url()else
                                '  (no proxy saved -> plain internet)'if _nm0!='off'else
                                '  (no network - every command runs offline)'))if _rec0 else'not recorded (created before csb tracked this)'
        if _nm0=='template':
            rows['net_mode']='template  (inherited; csb sent no policy)'
            rows['allow_out_applied']='(template policy)'
        _pol0=sbx_net_pol(c,_sid)
        _den0=sbx_net_deny(c,_sid)
        _dn0=_sbx_get(c,_sid).get('dns')or[]
        if _rec0 and _nm0 not in('off','template'):
            if not _pol0:rows['allow_out_applied']='(platform default - csb sent no policy)'
            elif '0.0.0.0/0' in _pol0:rows['allow_out_applied']='(all IPv4 allowed)'
            else:
                rows['allow_out_applied']=', '.join(_pol0)
                if _den0:
                    rows['allow_out_applied']+='  (only these allowed)'
                    if any(not _ao_is_cidr(x) for x in _pol0):rows['dns']='on  (implied by the domain rules)'
                    else:rows['dns']=('on  (%s)'%', '.join(dns_cidr(x)or x for x in _dn0))if _dn0 else 'off (domains will not resolve)'
        _pe0=(_auto_proxy_env().get('HTTPS_PROXY')or'(none)')if _nm0!='off' else'(none - --net off)'
        rows['proxy_for_exec']=_pe0 if _rec0 else'(per command: --env HTTPS_PROXY=…)'
        _stamp=_sbx_get(c,_sid).get('net_ts')
        if _rec0 and _stamp and _nm0!='template':
            _base=rows.get('net_mode')or _nm0
            rows['net_mode']='%s  (set by csb at %s)'%(_base,_disp(_stamp))
      except Exception:pass
    for _k,_v in list(rows.items()):
        _t=_tip(_k,_v)
        if _t:rows[_k]='%s  (%s)'%(_v,_t)
    used=set();secs=[]
    for nm,ks in _INFO_GRP:
        got=[(k,rows[k])for k in ks if k in rows];used.update(k for k,_ in got)
        if got:secs.append((nm,got))
    rest=sorted((k,v)for k,v in rows.items()if k not in used)
    if rest:secs.append(('OTHER',rest))
    if not secs:print('(no fields to show - empty server object; retry)');return
    _pn=_sw('dev_panel')
    for _n,_g in secs:
        if _n=='RUNTIME'and any(k=='runtime_snapshot'for k,_v in _g):_g.append(('','(runtime base - moves to the newest snapshot of this sandbox)'))
    _gw=max(CKVW,min(max([len(k)for _n,_g in secs for k,_v in _g]or[0]),20))
    _W=_termw();_cw=min(CRW,_W-1)if _W else CRW
    for i,(nm,g) in enumerate(secs):
        if i:print('')
        print(nm)
        w=_gw
        for k,v in g:
            sv=str(v)
            if not k:
                _tprint('%s    %s'%(TUI_VAL if _pn else'',sv),'    ',_W)
                continue
            if len(k)<=w and len('  %-*s  %s'%(w,k,sv))<=_cw:
                _gap='  '
                print('  %-*s%s%s%s'%(w,k,_gap,TUI_KV,sv)if _pn else'  %-*s%s%s'%(w,k,_gap,sv))
            else:
                _tprint('  %s%s'%(k,TUI_KV)if _pn else'  %s'%k,'  ',_W)
                if not _W:print('%s    %s'%(TUI_VAL if _pn else'',sv))
                else:_tprint('%s    %s'%(TUI_VAL if _pn else'',sv),'    ',_W)
def cmd_info(o,c):
    label=need_arg(o,'info: <id>');sb,_=_find_sb(label,c)
    if not sb:die(2,_infonope(label,c))
    if sb['state']!='running':
        d={**_ident(sb),'started_at':sb.get('ts'),'metadata':sb.get('meta')}
        if is_json(o):out_json(d);return 0
        _info_print(d,c);return 0
    try:info=_val(o,'reading %s'%label,lambda:_inst(sb,c).get_info())
    except Exception as ex:die(3,'get_info failed: %s'%ex)
    d=dict(info) if isinstance(info,dict) else({} if not hasattr(info,'to_dict') else info.to_dict())
    if not d:
        d={k:getattr(info,k,None) for k in('sandboxID','templateID','alias','domain','state','startedAt','endAt','cpuCount','cpuMilli','memoryMB','envdVersion','diskSizeMB','metadata')}
    try:
        inst=_inst(sb,c);host=inst.get_host(49983)
        d['port']=49983;d['url']=_url_of(host)
    except Exception:pass
    _m0=d.get('metadata')
    if isinstance(_m0,dict):
        _rid=_m0.get('cube.master.runtime.snapshot.id')or _m0.get('cube.master.runtime.restore.snapshot.id')
        if _rid:
            _nm=(led(c).get(_rid)or{}).get('name')
            if not _nm:
                _ns=((snap_facts(c)[0]or{}).get(_rid)or{}).get('names')or[]
                _nm=_ns[0]if _ns else None
            if _rid!=str(d.get('templateID')or''):
                d['runtime_snapshot']=('%s  (%s)'%(_rid,_nm))if _nm and _nm!=_rid else _rid
    try:
        _w0=sbx_net_saved(c,sb['id']);_p0=sbx_net_pol(c,sb['id'])
        _aod=(','.join(_p0)if _p0 else
              '(none - network off)'if _w0=='off'else
              '(from the template policy - run: csb tpl info %s)'%(sb.get('tpl')or'')if _w0=='template'else
              '(platform default)'if _w0 else
              '(not recorded - made by an older csb)')
    except Exception:_aod='(not recorded)'
    _id2={**_ident(sb),'allow_out':_aod}
    if is_json(o):
        out_json({**_id2,'info':d});return 0
    _info_print(d,c,_id2);return 0
_AGREE={'are':'is','were':'was','have':'has','go':'goes','carry':'carries','descend':'descends',
        'reference':'references','hang':'hangs','stay':'stays','do':'does','need':'needs','remain':'remains'}
_VBS='|'.join(sorted(_AGREE,key=len,reverse=True))
_NUMPL=re.compile(r'(\d+)\s+((?:[^\d\s]+\s+)*?)(\w+)\((s|es)\)(\s+(?:still|already|also|now|just|ever)\b)?(\s+(%s)\b)?'%_VBS)
def _nump(s):
    def r(m):
        n=int(m.group(1));out='%d %s%s%s%s'%(n,m.group(2),m.group(3),''if n==1 else m.group(4),m.group(5)or'')
        v=m.group(7)
        return out+(' '+(_AGREE[v]if n==1 else v)if v else'')
    return _NUMPL.sub(r,str(s))

def _pl(n,one,many=None):
    return '%d %s'%(n,one if n==1 else(many or one+'s'))
def _okl(what,sid,label=None,name=None,show_id=True):
    s0=str(sid or'');nm=(name or'').strip()or(label or'').strip()
    if not nm or s0.startswith(nm)or nm.startswith(s0):nm=s0[:8]
    print(('%s  %s\nid  %s'if show_id else'%s  %s')%(nm,what,s0)if show_id else'%s  %s'%(nm,what))
def _wait_stop(fd=None):
    import select as _sl
    try:_fd=sys.stdin.fileno()if fd is None else fd
    except Exception:return False
    if fd is None and not is_tty():return False
    try:
        if not _sl.select([_fd],[],[],0)[0]:return False
        b=os.read(_fd,1)
        if b!=b'\x1b':return False
        if _sl.select([_fd],[],[],0.04)[0]:
            os.read(_fd,64)
            return False
        return True
    except Exception:return False

def _wait_begin(fd=None):
    import termios as _tm,tty as _ty
    try:
        _fd=sys.stdin.fileno()if fd is None else fd
        old=_tm.tcgetattr(_fd);_ty.setcbreak(_fd);return _tty_keep(_fd,old)
    except Exception:return(fd,None)

def _wait_bg(fn):
    import threading as _th
    box={}
    def go():
        try:box['val']=fn()
        except BaseException as e:box['err']=e
    t=_th.Thread(target=go,daemon=True);t.start()
    return{'th':t,'box':box}

def _wait_guard(o):
    return(None,None)if is_json(o)else _wait_begin()

_TTY=[]
def _tty_keep(fd,old):
    h=(fd,old)
    if not any(f==fd for f,_o in _TTY):_TTY.append(h)
    return h
def _tty_drop(t):
    fd,old=t if isinstance(t,tuple)else(t,None)
    if fd is None:return
    for _i,(_f,_o)in enumerate(_TTY):
        if _f==fd and _o is old:_TTY.pop(_i);return
def _tty_back():
    import termios as _tm
    while _TTY:
        fd,old=_TTY.pop()
        try:_tm.tcsetattr(fd,_tm.TCSANOW,old)
        except Exception:pass
def _sig_cli(sig,frame=None):
    _tty_back()
    try:
        import signal as _sg
        sys.stdout.flush()
        sys.stderr.write('csb: %s - handing the terminal back; the operation keeps running on the platform (csb info shows it)\n'%_sg.Signals(sig).name);sys.stderr.flush()
    except Exception:pass
    os._exit(128+sig)
def _sig_install():
    import signal as _sg
    for _s in(_sg.SIGTERM,_sg.SIGHUP,_sg.SIGQUIT):
        try:_sg.signal(_s,_sig_cli)
        except Exception:pass
def _wait_restore(t):
    fd,old=t if isinstance(t,tuple)else(t,None)
    _tty_drop(t)
    if old is None or fd is None:return
    import termios as _tm
    try:_tm.tcsetattr(fd,_tm.TCSANOW,old)
    except Exception as _e:_swallow('wait restore',_e)

def _wait_secs():return _sw('cube_wait')
def _exec_secs():return _sw('cube_exec_wait')
def _connect_secs():return _sw('cube_connect_wait')
def _http_secs():return _sw('cube_http_wait')
def _stop_secs():return _sw('cube_stop_wait')
def _lim(x):
    return x
_STOPWATCH=[None]
def _watch(o,msg,fn,lim):
    import time as _t
    _STOPWATCH[0]=None
    j=_wait_bg(fn);t0=_t.time();res='ok';drew=[False]
    _json=is_json(o);_nospin=_sw('auto_no_spin')
    _key=not _json
    _tick=not _json and not _nospin and sys.stderr.isatty() and bool(msg)
    if not _json and not _nospin and not sys.stderr.isatty() and msg:sys.stderr.write(msg+'\n');sys.stderr.flush()
    _wt=_wait_guard(o)
    try:
        while True:
            j['th'].join(0.25)
            if not j['th'].is_alive():break
            el=_t.time()-t0
            if el>=lim:res='still';break
            if _key:
                if _wait_stop():res='stop';break
                if _tick and el>=1.0:
                    sys.stderr.write('\r   %s   %ds / %ds   '%(msg,int(el),int(lim)))
                    sys.stderr.flush();drew[0]=True
    finally:
        if drew[0]:
            _dt=_t.time()-t0
            sys.stderr.write('\r   %s   done in %ds%s\n'%(msg,int(_dt),' '*4));sys.stderr.flush()
        if not is_json(o):_wait_restore(_wt)
    if res!='ok'and not j['th'].is_alive():res='ok'
    if res!='ok':_STOPWATCH[0]=res
    return res,j
def _re(j):
    e=j['box'].get('err')
    if isinstance(e,SystemExit):raise e
    return e
def _stopmsg(msg,res,lim,k,hint=''):
    if res=='stop':t='%s: stopped watching - the request is already with the server and keeps running there'%msg
    else:t='%s: no answer for %ds - the request is already with the server and keeps running there (raise it: %s)'%(msg,int(lim),k)
    return t+('\n'+hint if hint else'')
def _val(o,msg,fn,lim=None,k='CSB_STOP_WAIT',hint=''):
    lim=_lim(_stop_secs())if lim is None else lim
    res,j=_watch(o,msg,fn,lim)
    if res=='ok':
        e=_re(j)
        if e is not None:raise e
        return j['box'].get('val')
    die(1 if res=='stop'else 3,_stopmsg(msg or 'the request',res,lim,k,hint))

def _wait_state(sid,want,o,c,job=None):
    import time as _t
    st=lambda:next((x['state'] for x in fetch_sbs(c) if x['id']==sid),None)
    lim=_wait_secs();i=0;res='ok'
    _wt=(None,None)if is_json(o)else _wait_begin()
    try:
        while True:
            if job is not None and job['box'].get('err'):
                if not is_json(o):sys.stderr.write('\n')
                res='err';break
            _done=job is None or not job['th'].is_alive()
            if _done and st()==want:break
            if not is_json(o):
                if _wait_stop():
                    sys.stderr.write('\n');res='stop';break
                if not _sw('auto_no_spin'):sys.stderr.write('\r   waited %ds / %ds   '%(i*2,lim));sys.stderr.flush()
            _t.sleep(2.0);i+=1
            if i*2>=lim and not(_done and st()==want):
                if not is_json(o):sys.stderr.write('\n')
                res='still';break
    finally:
        if not is_json(o):_wait_restore(_wt)
    if not is_json(o)and res=='ok':sys.stderr.write('\n')
    if not is_json(o)and res!='ok':
        now=st()or'?'
        if res=='stop':err('stopped watching - the platform keeps working on it')
        else:err('still %s after %ds - the platform is still working on it   (raise CSB_WAIT to wait longer)'%(now,i*2))
    return res

def _wait_end(o,c,sb,label,res,want):
    if res=='ok':return None
    sid=sb['id'];now=next((x['state'] for x in fetch_sbs(c) if x['id']==sid),sb.get('state')or'?')
    note=('stopped watching - the platform keeps working on it'if res=='stop'
          else'still %s after %ds'%(now,_wait_secs()))
    if is_json(o):out_json({'sandbox_id':sid,'label':label,'state':now,'note':note})
    return 1 if res=='stop'else 3
def _pause_rows(live):
    return[{'id':s['id'],'label':(s.get('label')or'').strip()or short_id(s['id'])}for s in live]
def _pause_all(o,c):
    sbs=fetch_sbs(c)
    live=[s for s in sbs if s.get('state')=='running']
    if not live:
        if is_json(o):out_json({'paused':[],'failed':[],'note':'nothing is running'})
        else:err('nothing is running')
        return 0
    rows=_pause_rows(live)
    if is_json(o)and o.get('dry-run'):
        out_json({'dry_run':True,'action':'pause all %s'%_pl(len(live),'sandbox','sandboxes'),'would_pause':rows})
        return 0
    if not is_json(o):
        print('would pause %s - the whole cluster, not only your ledger:'%_pl(len(live),'sandbox','sandboxes'))
        for r in rows:print('  %-28s %s'%(r['label'],r['id']))
    dry_only(o,'pause all running %s'%_pl(len(live),'sandbox','sandboxes'),why='pausing %s'%_pl(len(live),'sandbox','sandboxes'))
    if not confirm(o,'pause all %s running? (this is the whole cluster, not only your ledger)'%_pl(len(live),'sandbox','sandboxes'),why='pausing %s'%_pl(len(live),'sandbox','sandboxes')):return 1
    ok=[];bad=[]
    for s in live:
        nm=(s.get('label')or'').strip()or short_id(s['id'])
        oo=dict(o);oo['all']=False;oo['_']=[s['id']]
        try:rc=cmd_pause(oo,c)
        except SystemExit as ex:rc=ex.code if isinstance(ex.code,int)else 1
        except Exception as ex:rc=1;err('pausing %s failed: %s'%(nm,ex))
        (ok if not rc else bad).append(nm)
    if is_json(o):out_json({'paused':ok,'failed':bad})
    else:err('paused %d of %d%s'%(len(ok),len(live),(' - failed: '+', '.join(bad))if bad else''))
    return 0 if not bad else 3
def _net_plan(o,c,sb):
    """`csb net` flags -> (mode, payload, allow, deny, dns); dies rc2 on a bad shape.

    A whitelist reads the sandbox resolver (read-only, the same source `csb start` uses) and
    folds it into allow_out, because a replacement that drops DNS cannot resolve a name."""
    _l=sb.get('label')or(sb.get('id')or'')[:8]
    _netf=o.get('net')
    _has_net=(_netf not in(None,True,''))or bool(o.get('no-net'))
    _has_ao=o.get('allow-out')is not None
    if _has_net and _has_ao:
        die(2,'net: --net off and --allow-out are two different networks - give one\n'
               '  off        csb net %s --net off\n'
               '  whitelist  csb net %s --allow-out 10.0.0.0/8,192.168.1.0/24\n'
               '  all IPv4   csb net %s --allow-out all'%(_l,_l,_l))
    if not _has_net and not _has_ao:
        die(2,'net: say what the network should become\n'
               '  whitelist  csb net %s --allow-out 10.0.0.0/8   (only these; DNS kept)\n'
               '  all IPv4   csb net %s --allow-out all\n'
               '  no network csb net %s --net off'%(_l,_l,_l))
    if _has_net:
        if net_mode(o)!='off':
            die(2,'net: --net only takes off - the platform replaces the whole policy\n'
                   '  all IPv4   csb net %s --allow-out all\n'
                   '  whitelist  csb net %s --allow-out <cidr[,cidr]>'%(_l,_l))
        return'off',{'allow_internet_access':False,'allow_out':[],'deny_out':[]},[],[],[]
    _ao=_norm_allow(_allow_out(o))
    if not _ao:
        if o.get('dns-server'):sys.stderr.write('csb: --dns-server is only used by a whitelist - ignored here\n')
        return'on',{'allow_internet_access':True,'allow_out':[],'deny_out':[]},[],[],[]
    _srv=[]
    try:
        _cr=_inst(sb,c).commands.run('cat /etc/resolv.conf',timeout=10)
        _srv=resolv_servers(getattr(_cr,'stdout','')or'')
    except Exception as _e:_swallow('dns read',_e)
    _ov=str(o.get('dns-server')or os.environ.get('CSB_DNS')or'').strip()
    if _ov:
        try:
            import ipaddress as _ipa;_ipa.ip_address(_ov)
        except Exception:die(2,'--dns-server: not an IP address: %s\nfix   --dns-server 119.29.29.29'%_ov)
        _srv.append(_ov)
    _srv=list(dict.fromkeys(_srv))
    if not _srv:
        die(3,'net: could not read the DNS resolver of %s (/etc/resolv.conf) - a whitelist without DNS cannot resolve a name\n'
               '  fix   csb net %s --allow-out ... --dns-server <ip>'%(sb.get('id'),sb.get('id')))
    _pol=list(dict.fromkeys(list(_ao)+[x for x in(dns_cidr(v)for v in _srv)if x]))
    return'on',{'allow_internet_access':True,'allow_out':_pol,'deny_out':['0.0.0.0/0']},_pol,['0.0.0.0/0'],_srv
def cmd_net(o,c):
    label=need_arg(o,'net: <sandbox id>')
    if len(o.get('_')or[])>1:die(2,'net: one sandbox at a time - run it once per id')
    sb,_=_find_sb(label,c)
    if not sb:die(2,_sbnope(label,c))
    _id=sb['id'];_l=sb.get('label')or _id[:8]
    if sb.get('state')!='running':
        die(2,'net: %s is %s - the network only changes while the sandbox is running\n'
               '  fix   csb resume %s --yes, then retry'%(_l,sb.get('state')or'unknown',_id))
    mode,payload,pol,deny,dns=_net_plan(o,c,sb)
    if o.get('dry-run'):
        if is_json(o):
            out_json({'dry_run':True,'sandbox_id':_id,'allow_out':payload['allow_out'],
                      'deny_out':payload['deny_out'],'allow_internet_access':payload['allow_internet_access'],
                      'dns':list(dns)})
        else:
            sys.stdout.write('dry-run: POST /sandboxes/%s/network - nothing was changed\n'%_id)
            out(payload)
        return 0
    if not o.get('yes'):
        if not is_tty():
            _w=('--net off'if mode=='off'else
                '--allow-out all'if not payload['allow_out']else'--allow-out <cidr[,cidr]>')
            die(2,'--yes required for changing the network of %s (non-tty) - pass --yes\n'
                   '  fix   csb net %s %s --yes'%(_l,_id,_w))
        if not _yn('csb: update network of %s (%s)'%(_l,_id[:8])):return 1
    try:
        _inst(sb,c).update_network(payload)
    except Exception as ex:
        _t=str(ex)
        _h=''
        if 'is not running' in _t or '1304' in _t:
            _h='\n  fix   csb resume %s --yes, then retry'%_id
        die(3,'network update failed: %s%s'%(_why_server(ex),_h),raw=_t)
    _save_sbxenv(c,_id,_saved_sbxenv(c,_id),mode,pol,deny,dns,ts=_now())
    _aia=bool(payload.get('allow_internet_access'))
    if is_json(o):
        out_json({'sandbox_id':_id,'allow_out':list(payload['allow_out']),'deny_out':list(payload['deny_out']),
                  'allow_internet_access':_aia,'dns':list(dns)})
        return 0
    _okl('network updated',_id,label,sb.get('label'),show_id=False)
    print('  allow_internet_access  %s'%('true'if _aia else'false'))
    print('  allow_out              %s'%(', '.join(payload['allow_out'])
                                       or'(none - no whitelist, the platform default applies)'))
    print('  deny_out               %s'%(', '.join(payload['deny_out'])
                                       or'(none - the platform keeps its default)'))
    if dns:print('  dns                    %s'%', '.join(dns))
    err('note  the platform takes the whole policy at once - every field not listed here is now empty')
    return 0
def cmd_pause(o,c):
    if o.get('all'):return _pause_all(o,c)
    label=need_arg(o,'pause: <id>');sb,_=_find_sb(label,c)
    if not sb:die(2,_sbnope(label,c))
    dry_only(o,'pause %s'%label,why='pausing %s'%label)
    if sb['state']=='paused':
        if is_json(o):out_json({'sandbox_id':sb['id'],'label':label,'state':'paused','note':None})
        else:_okl('already paused',sb['id'],label,sb.get('label'),show_id=False)
        return 0
    if not is_json(o):err('pausing %s'%label)
    _wt=_wait_guard(o)
    try:
        _job=_wait_bg(lambda:_inst(sb,c).pause(wait=False))
        _res=_wait_state(sb['id'],'paused',o,c,_job)
    finally:
        _wait_restore(_wt)
    if _job['box'].get('err'):die(3,'pause failed: %s'%_why_server(_job['box']['err']),raw=str(_job['box']['err']))
    rc=_wait_end(o,c,sb,label,_res,'paused')
    if rc is not None:return rc
    if is_json(o):out_json({'sandbox_id':sb['id'],'label':label,'state':'paused','note':None})
    else:_okl('paused',sb['id'],label,sb.get('label'),show_id=False)
    return 0
def cmd_resume(o,c):
    label=need_arg(o,'resume: <id>');sb,_=_find_sb(label,c)
    if not sb:die(2,_sbnope(label,c))
    _tm=o.get('timeout');_secs=None
    if _tm is not None:
        _e=timeout_err(_tm)
        if _e:die(2,'--timeout: %s'%_e)
        _secs=_int(_tm,None,'--timeout')
        if _secs is None or _secs<=0:
            die(2,'resume --timeout needs a positive number of seconds, got %r\n  why   the idle TTL is replaced from this resume (not added)\n  fix   csb resume <id> --timeout <sec>'%_tm)
    dry_only(o,'resume %s%s'%(label,''if _secs is None else' --timeout %d'%_secs),why='resuming %s'%label)
    if sb['state']=='running':
        if _secs is not None:
            die(2,'resume --timeout needs a paused sandbox: %s is already running\nfix   csb timeout %s %d'%(label,sb['id'],_secs))
        if is_json(o):out_json({'sandbox_id':sb['id'],'label':label,'state':'running','note':None,'timeout':None})
        else:_okl('already running',sb['id'],label,sb.get('label'),show_id=False)
        return 0
    if sb['state']=='paused':
        import time as _t
        def _go():
            _last=None
            for _ in range(6):
                try:
                    _raw(sb,c).resume(_secs)
                    return
                except Exception as _e:
                    _last=_e
                    _t.sleep(1)
            if _last is not None:raise _last
        _wt=_wait_guard(o)
        try:
            _job=_wait_bg(_go)
            _res=_wait_state(sb['id'],'running',o,c,_job)
        finally:
            _wait_restore(_wt)
        if _job['box'].get('err'):
            _e=_job['box']['err']
            _hint=(''
                   if '130497'not in str(_e)else
                   '\n  why   the node could not bring the guest agent up (envd init)'
                   '\n  fix   retry once; still failing -> start a fresh sandbox from the template')
            die(3,'resume failed: %s%s'%(_why_server(_e),_hint),raw=str(_e))
        rc=_wait_end(o,c,sb,label,_res,'running')
        if rc is None:
            _t.sleep(1.5)
            _now=next((x['state'] for x in fetch_sbs(c) if x['id']==sb['id']),None)
            if _now is not None and _now!='running':
                die(3,'resume did not stick: %s is %s again right after the call\n'
                       '  why   accepted, then rolled back (envd init)\n'
                       '  fix   retry once; still the same -> csb kill %s --yes   (csb info %s)'
                    %(label,_now,sb['id'],sb['id']))
    else:
        if _secs is not None:
            die(2,'resume --timeout needs a paused sandbox: %s is %s'%(label,sb.get('state')or'unknown'))
        rc=_wait_end(o,c,sb,label,_wait_state(sb['id'],'running',o,c),'running')
    if rc is not None:return rc
    if is_json(o):out_json({'sandbox_id':sb['id'],'label':label,'state':'running','note':None,'timeout':_secs})
    else:
        _nm=(sb.get('label')or label or sb['id'])
        print('%s  resumed  %s'%(_nm,sb['id']))
        if _secs is not None:print('idle TTL %d s'%_secs)
    return 0
def cmd_timeout(o,c):
    label=need_arg(o,'timeout: <id> <seconds>')
    if len(o['_'])<2:die(2,'timeout: <id> <seconds>  (or: timeout <seconds> <id>)')
    if not timeout_err(o['_'][0]) and timeout_err(o['_'][1]):
        label,sec_s=o['_'][1],o['_'][0]
    else:
        sec_s=o['_'][1]
    _e=timeout_err(sec_s)
    if _e:die(2,'timeout: %s'%_e)
    sec=_int(sec_s,None,'seconds')
    sb,_=_find_sb(label,c)
    if not sb:die(2,_sbnope(label,c))
    dry_only(o,'set the timeout of %s to %s'%(label,sec),why='setting the timeout of %s'%label)
    _need_run(sb,'csb timeout')
    try:_inst(sb,c).set_timeout(int(sec))
    except Exception as ex:die(3,'timeout failed for %s: %s'%(label,_why_server(ex)),raw=str(ex))
    if is_json(o):out_json({'sandbox_id':sb['id'],'label':label,'timeout':int(sec)})
    else:_okl('timeout %ss'%sec,sb['id'],label,sb.get('label'),show_id=False)
    return 0
def _url_of(host):
    return host if '://' in host else 'http://%s/'%host

def cmd_url(o,c):
    label=need_arg(o,'url: <id> [port]');port=_int(o['_'][1] if len(o['_'])>1 else None,49983,'port')
    sb,_=_find_sb(label,c)
    if not sb:die(2,_sbnope(label,c))
    _need_run(sb,'csb url')
    try:
        inst=_inst(sb,c);host=inst.get_host(port)
    except Exception as ex:die(3,'get_host failed: %s'%ex)
    url=_url_of(host)
    if is_json(o):
        out={'sandbox_id':sb['id'],'label':label,'port':port,'url':url}
        try:
            out['domain']=inst.domain;out['token_hint']='envdAccessToken via server'
        except Exception:pass
        out_json(out)
    else:
        print(url)
        try:print('domain: %s'%inst.domain)
        except Exception:pass
    return 0
def _recycle_snapshot(c,sid,tries=5,wait=2.0):
    """A failed clone must not leave its temporary snapshot behind.

    Tries delete_snapshot, retrying only while the platform says the refcount is still
    draining (130409). Returns (True, None) after removing the ledger row, else (False, err)."""
    import time as _t
    err=None
    for i in range(tries):
        try:
            _Sandbox().delete_snapshot(sid,config=sdk(c))
            led(c).pop(sid,None);save_led(c)
            return True,None
        except Exception as ex:
            err=ex
            if '130409'not in str(ex):return False,ex
            if i<tries-1:_t.sleep(wait)
    return False,err
def cmd_clone(o,c):
    label=need_arg(o,'clone: <id>');n=_int(o.get('n'),1,'--n');cc=_int(o.get('concurrency'),1,'--concurrency')
    if n<1:die(2,'--n must be >= 1 (got %d)\n    omit --n when you only need one sandbox'%n)
    if cc<1:die(2,'--concurrency must be >=1, got %d'%cc)
    if n>20 and not confirm(o,'clone %d sandboxes? (bulk > 20: double-check)'%n,why='cloning %d sandboxes'%n):return 1
    ot=_ot_check(o.get('on-timeout'))
    tm=_tmo(o,2592000)
    if o.get('label'):die(2,'clone: --label unsupported - use  csb start <snapshot-id> --label <name> --family <fam>')
    sb,_=_find_sb(label,c)
    if not sb:die(2,_sbnope(label,c))
    if sb['state']!='running':die(3,'clone needs a running sandbox (%s is %s)\nfix   resume it first: csb resume %s --yes'%((sb.get('label')or sb['id']),sb['state'],sb['id']))
    dry_only(o,'clone %s into %s'%(label,_pl(n,'sandbox','sandboxes')),why='cloning %d sandboxes'%n)
    fam=sb.get('family')
    if not fam:
        if not o.get('family'):die(3,'family unknown for %s: pass --family (D-S)'%label)
        fam=o['family']
    si=_inst(sb,c).create_snapshot()
    snap_id=si.snapshot_id if not isinstance(si,str) else si
    _snap_ledger_write(snap_id,{'label':label,'fam':fam,'origin':sb['id'],'ts':_now()},c)
    entries=reg(c)['entries'];hw=reg(c)['family_highwater']
    import threading
    made=[];warn=None;born=[];lk=threading.Lock();sdone=[False]
    try:
        jobs=_reserve_labels(c,fam,n)
        def mk(job):
            lab,ns=job;meta=_meta(fam,'clone',label,lab,ns)
            nsb=_Sandbox().create(template=snap_id,timeout=tm,metadata=meta,lifecycle={'on_timeout':ot},config=sdk(c))
            with lk:born.append((nsb.sandbox_id,lab))
            return nsb.sandbox_id,lab,ns,_svts(nsb._data)
        if cc>1 and n>1:
            from concurrent.futures import ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=min(cc,n)) as ex:res=list(ex.map(mk,jobs))
        else:res=[mk(j) for j in jobs]
        sv=_srv_started(c,{x[0]for x in res})
        for sid,lab,ns,ts0 in res:
            entries[sid]={'label':lab,'family':fam,'nseq':ns,'kind':'clone','parent':label,'ancestor':reg(c)['entries'].get(sb['id'],{}).get('ancestor')or fam,'template_id':snap_id,'ts':sv.get(sid)or ts0 or _now()}
            made.append({'sandbox_id':sid,'label':lab})
            _r0=_sbx_get(c,sb['id'])
            if _r0:
                _save_sbxenv(c,sid,_saved_sbxenv(c,sb['id']),_r0.get('mode'),_r0.get('pol'),_r0.get('deny'),_r0.get('dns'))
    except Exception as ex:
        sdone[0]=True;_dead=[];_stuck=[]
        for sid0,lab0 in born:
            try:_Sandbox().connect(sid0,timeout=_connect_secs(),config=sdk(c)).kill();_dead.append('%s (%s)'%(lab0,short_id(sid0)))
            except Exception:_stuck.append(sid0)
        _snap_line=''
        if snap_id:
            _ok,_serr=_recycle_snapshot(c,snap_id)
            if _ok:_snap_line='  temp snapshot %s recycled (the failed clone leaves nothing behind)'%snap_id
            else:
                _snap_line='  temp snapshot %s kept (%s)'%(short_id(snap_id),_serr)
                _snap_line+='\n  fix   csb snaprm %s --yes'%snap_id
        _l=['clone failed after %d of %s: %s'%(len(born),_pl(n,'sandbox','sandboxes'),_why_server(ex)),
            ('  killed what did come up: %s'%', '.join(_dead)) if _dead else '  nothing came up, so there is nothing to clean up']
        if _stuck:_l.append('  could NOT kill these - they are still running, remove them yourself:  csb kill %s --yes'%' '.join(_stuck))
        if _snap_line:_l.append(_snap_line)
        _l.append('  hint: the source sandbox must still be running, and the cluster must have room')
        die(3,'\n'.join(_l),raw=str(ex))
    finally:
        if not sdone[0]:
            if snap_id:
                warn='temp snapshot %s kept'%short_id(snap_id)
                warn+='\nfix   csb snaprm %s --yes'%snap_id
                if not is_json(o):err(warn)
    save_reg(c)
    if not o.get('async'):
        _dn=(sb.get('label')or'').strip()or str(sb.get('id')or label)[:8]
        if not is_json(o):err('cloning %s -> %s'%(_dn,_pl(n,'sandbox','sandboxes')))
        for m in made:
            sid=m['sandbox_id'];st=lambda sid=sid:next((x['state'] for x in fetch_sbs(c) if x['id']==sid),None)
            if wait_poll(st,'running',45,2.0)[0] is False:die(3,'clone timeout: %s'%sid)
    if is_json(o):
        d={'made':made}
        if warn:d['warning']=warn
        out_json(d)
    else:
        for m in made:_okl(('requested (--async, not waited)'if o.get('async')else'cloned'),m['sandbox_id'],m['label'])
    return 0

def cmd_commit(o,c):
    if len(o['_'])>1:
        die(2,'commit: one sandbox at a time, got %d (%s) - run it once per sandbox'%(len(o['_']),', '.join(o['_'][:3])))
    label=need_arg(o,'commit: <id>');sb,_=_find_sb(label,c)
    if not sb:die(2,_sbnope(label,c))
    if sb['state']!='running':die(3,'commit needs a running sandbox (%s, %s)\n  fix   csb resume %s --yes'%((sb.get('label')or sb['id']),sb['state'],sb['id']))
    if o.get('alias'):
        _ae=alias_err(o['alias'])
        if _ae:die(2,_ae)
        _own=alias_taken(c,'',o['alias'])
        if _own:alias_clash_die(o['alias'],_own,'commit')
    fam=sb.get('family')
    if not fam and o.get('family'):fam=o['family']
    dry_only(o,'commit %s into a template'%label,why='committing %s'%label)
    exe=_env('CSB_CUBEMASTERCLI')or'cubemastercli'
    _st=None if is_json(o) else _spin('commit %s:'%label)
    try:
        p=subprocess.run([exe]+cm_addr()+['tpl','commit','--sandbox-id',sb['id']],capture_output=True,text=True,timeout=_wait_secs())
    except FileNotFoundError:die(3,'%s not found: install CubeMaster CLI (see INSTALL.md)'%exe)
    except subprocess.TimeoutExpired:die(3,'commit timed out after %ds (raise CSB_WAIT)'%_wait_secs())
    finally:
        if _st:_st()
    blob=(p.stdout or '')+(p.stderr or '')
    if p.returncode!=0:die(3,'commit failed %s - retry, or run it yourself:  %s tpl commit %s'%((blob.strip() or'(no reason given by the server)')[:800],cm_txt(),sb['id']))
    m=re.search(r'\b(tpl-[A-Za-z0-9]+)\b',blob)
    if not m:die(3,'commit failed: unparsable template id --- %s'%(blob.strip()[:800]))
    tid=m.group(1)
    tpls=_tpl_rows2(c);existing=[t['alias'] for t in tpls if t['alias']]
    date=datetime.datetime.now().strftime('%Y%m%d')
    alias=o.get('alias')or tpl_alias(fam or label,date,existing)
    if o.get('alias'):
        ae=alias_err(alias)
        if ae:die(2,ae)
    set_alias_cli(c,tid,alias)
    ts0=_srv_tpl_ts(c,tid)
    reg(c)['templates'][tid]={'alias':alias,'family':alias,'ts':ts0 or _now(),'local_labels':True};save_reg(c)
    if is_json(o):out_json({'template_id':tid,'alias':alias})
    else:
        _okl('committed',tid,alias)
    return 0
def cmd_tpl_ls(o,c):
    ts=sorted([t for t in tpl_rows(c) if not t['is_snap']],key=lambda t:_tkey(t['ts']),reverse=True)
    rows=[[t['alias']or'-',t['id'],t['status'],_disp(t['ts'])] for t in ts]
    if is_json(o):out_json([{'template_id':t['id'],'alias':t['alias'],'status':t['status'],'is_snapshot':t['is_snap'],'created_at':t['ts']} for t in ts]);return 0
    if not rows:print('(no templates on this cluster - build one:  csb tpl build --image <ref> --alias <name>)')
    else:fmt(['ALIAS','ID','STATUS','CREATED'],rows)
    return 0
def cmd_tpl_info(o,c):
    arg=need_arg(o,'tpl info: <alias|id>')
    ts=tpl_rows(c);t=next((x for x in ts if x['alias']==arg or x['id']==arg),None)
    if not t:die(2,'unknown template: %s (see tpl ls)'%arg)
    p=tpl_net_policy(c,t['id'])
    net=None if not p else {'allow_out':list(p.get('allow')or[]),'deny_out':list(p.get('deny')or[]),
                            'dns':list(p.get('dns')or[]),'allow_internet_access':p.get('aia')}
    if is_json(o):out_json({**t,'network':net});return 0
    for k,v in t.items():
        if v in(None,''):continue
        print('%-12s %s'%(k,_disp(v)if k=='ts'else v))
    print('NETWORK')
    for x in tpl_net_lines(p):print('  '+x)
    print('  %-11s%s'%('proxy','not stored (injected per exec/shell; csb info shows it)'))
    return 0
def alias_err(a):
    if not a or not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,63}',a)or a.startswith(('tpl-','snap-')):
        return'bad alias: lowercase letters/digits/hyphens 1-64, no tpl-/snap- prefix'
def _tpl_rows2(c=None):
    a=tpl_rows(c);b=tpl_rows(c)
    if len(b)<=len(a):return a
    seen={t['id']for t in a}
    return a+[t for t in b if t['id']not in seen]
def alias_taken(c,tid,alias):
    try:
        for t in _tpl_rows2(c):
            if t['id']!=tid and (t.get('alias')or'').lower()==alias.lower():return t['id']
    except Exception as ex:
        die(3,'alias check failed (%s) - retry:  cubemastercli %s list'%(_why_server(ex),cm_txt()),raw=str(ex))
    return None
def alias_clash_die(alias,own,what='tpl alias'):
    die(2,'%s refused: %r is taken by %s\nfix   pick another name, or clear it on %s:  cubemastercli %s template set-alias --template-id %s --clear'%(what,alias,own,own,cm_txt(),own))
def cmd_tpl_alias(o,c):
    if len(o['_'])<2:die(2,'tpl alias: <template id|alias> <new-alias>')
    tid,alias=o['_'][0],o['_'][1]
    if tid.startswith('snap-'):die(2,'snap-* cannot take an alias\nfix   csb snap <sandbox> <name>        csb snaprm <id> --yes')
    _t=next((x for x in _tpl_rows2(c) if x['id']==tid or (x.get('alias')or'')==tid),None)
    if not _t:die(2,'unknown template: %s (see tpl ls)'%tid)
    if _t.get('is_snap'):
        die(2,'%s is a snapshot, not a template - use  csb snap <sandbox> <name>'%_t['id'])
    tid=_t['id'];_old=_t.get('alias')or''
    ae=alias_err(alias)
    if ae:die(2,ae)
    _own=alias_taken(c,tid,alias)
    if _own:alias_clash_die(alias,_own)
    dry_only(o,'set the alias of %s to %s'%(_old or tid,alias),why='setting the alias %s'%alias)
    info=set_alias_cli(c,tid,alias)
    _regT=reg(c).setdefault('templates',{}).setdefault(tid,{})
    _regT['alias']=alias
    _regT['family']=alias
    _hist=list(_regT.get('alias_history')or[])
    if _old and _old not in _hist:_hist.append(_old)
    if _hist:_regT['alias_history']=_hist
    _hw=reg(c).setdefault('family_highwater',{})
    if _old and not _hw.get(_old):
        try:_hw[_old]=0 if _CMIT.match(_old) else int(_hw.get(_regT.get('family'))or 0)
        except Exception:_hw[_old]=0
    _fresh=bool(_old and _old!=alias and _hw.get(alias)is None and not alias_has_resources(c,alias))
    _mv=alias_hw_move(_hw,_old,alias)if _old else None
    if _fresh:
        _hw[alias]=0;_mv=0
    _rc=False
    if _old and _old!=alias:
        _rc=alias_hw_reclaim(c,_old)
        if _rc:
            _hw.pop(_old,None)
    if _old:save_reg(c)
    if is_json(o):out_json({'template_id':tid,'alias':alias,'moved_highwater':_mv,'reclaimed':_rc})
    else:
        print('%s -> %s'%(tid,alias))
        if _mv:err('note: family counter carried over from %r: high-water %d - next default label %s'%(_old,_mv,label_default(alias,nseq_next(reg(c).get('entries')or{},reg(c).get('family_highwater')or{},alias))))
        if _rc:err('note: reclaimed high-water key %r (no sandbox/snapshot uses that prefix)'%_old)
    return 0
def cmd_tpl_clean_hw(o,c):
    hw=dict(reg(c).get('family_highwater')or{})
    keep=set()
    try:
        for t in tpl_rows(c):
            if t.get('is_snap'):continue
            if t.get('alias'):keep.add(t['alias'])
            _r=((reg(c).get('templates')or{}).get(t['id'])or{})
            if _r.get('family'):keep.add(_r['family'])
            for a in(_r.get('alias_history')or[]):keep.add(a)
    except Exception:pass
    for e in(reg(c)['entries']or{}).values():
        if e.get('family'):keep.add(e['family'])
    for e in(led(c)or{}).values():
        if e.get('fam'):keep.add(e['fam'])
    try:
        for s in fetch_sbs(c):
            if s.get('family'):keep.add(s['family'])
    except Exception:pass
    dead=sorted((k for k in hw if k not in keep),key=lambda k:str(k))
    if not dead:
        print(_nump('clean-hw: nothing to drop - all %d high-water key(s) are still reachable'%len(hw)));return 0
    if o.get('dry-run')or not o.get('yes'):
        print(_nump('clean-hw: %d dead high-water key(s) (dry-run - pass --yes to drop)'%len(dead)))
        for k in dead:print('  %-24s %s'%(k,hw.get(k)))
        if keep:print('kept: %s'%', '.join(sorted(keep,key=str))[:240])
        return 0
    import shutil
    _p=_hw_path(c['reg'])
    try:
        _bk='%s.bak-%s'%(_p,datetime.datetime.now().strftime('%Y%m%d-%H%M%S'))
        shutil.copy2(_p,_bk)
        print('clean-hw: backed up %s'%_bk)
    except Exception as ex:
        sys.stderr.write('clean-hw: backup skipped (%s) - continuing\n'%ex)
    for k in dead:hw.pop(k,None)
    _hw_save(c['reg'],hw)
    _r=reg(c)['family_highwater']
    for k in dead:_r.pop(k,None)
    save_reg(c)
    print(_nump('clean-hw: dropped %d key(s): %s'%(len(dead),', '.join(map(str,dead)))))
    return 0
def tpl_lineage_snaps(c,tid):
    live={s['id']:s.get('tpl')for s in fetch_sbs(c)}
    got=fetch_snap_origins(c)or{}
    return([k for k,o in got.items()if o and live.get(o)==tid],sum(1 for o in got.values()if o and o not in live))
def cmd_tpl_rm(o,c):
    arg=need_arg(o,'tpl rm: <alias|template-id>')
    ts=tpl_rows(c)
    t=next((x for x in ts if x['alias']==arg or x['id']==arg or(x['id'].startswith(arg)and len(arg)>=24)),None)
    if not t:die(2,'unknown template: %s (see tpl ls)'%arg)
    tid=t['id']
    if tid.startswith('snap-'):die(2,'tpl rm refuses snapshot templates: %s (delete snapshots with snaprm %s)'%(t['alias']or tid,tid))
    kids=[x for x,e in(reg(c).get('entries')or{}).items()if e.get('template_id')==tid or e.get('family')==(t.get('alias')or'')]
    snaps=[x for x,v in led(c).items()if(v or{}).get('origin')in kids]
    if snaps:
        err('WARN: %d snapshot(s), %s lineage - delete may collect rootfs; keep template.%s'%(len(snaps),t.get('alias')or tid,'\n'.join('    '+x for x in _snap_argv(snaps[:3]))))
    att,unk=tpl_lineage_snaps(c,tid)
    if o.get('dry-run'):
        _w='delete template %s (%s)'%(t['alias']or tid,tid)
        if att:_w+=' - would be REFUSED: %d server snapshot(s) still descend'%len(att)
        if is_json(o):out_json({'dry_run':True,'action':_w,'template_id':tid})
        else:sys.stdout.write('dry-run: %s - nothing was changed\n'%_w)
        return 0
    if att:
        _m=('tpl rm refused: %s - %s\nfix   %s\n      or:  csb tpl rm %s --force'%(t.get('alias')or tid,_pl(len(att),'snapshot still descends','snapshots still descend'),'\n      '.join(_snap_argv(att[:4])),t.get('alias')or tid))
        if not o.get('force'):die(2,_m)
        err('WARN: forcing delete of %s - %s'%(t.get('alias')or tid,
            _pl(len(att),'server-side snapshot still descends','server-side snapshots still descend')))
    if unk and att:err('%s of %s %s (sha256 risk).'%(_pl(unk,'snapshot','snapshots'),t.get('alias')or tid,
        _pl(unk,'has no live source','have no live source')))
    if t.get('deleted'):
        reg(c)['templates'].pop(tid,None);_TPL_DEL.add(tid);save_reg(c)
        if is_json(o):out_json({'template_id':tid,'alias':t['alias']or None,'already_gone':True})
        else:print('template %s (%s) was already gone from the server - local record removed'%(t['alias']or tid,tid))
        return 0
    if not o.get('yes')and not o.get('dry-run'):
        for k in('id','alias','status','ts'):
            v=t.get(k)
            if k=='ts'and v:v=_disp(v)
            if v not in(None,''):print('  %-9s %s'%(k,v))
        if not is_tty():die(2,'tpl rm deletes a template; pass --yes on a non-tty\n  fix   csb tpl rm <alias|id> --yes')
        if not _yn('delete template %s'%(t['alias']or short_id(tid))):return 1
    exe=_env('CSB_CUBEMASTERCLI')or'cubemastercli'
    try:p=subprocess.run([exe]+cm_addr()+['tpl','delete','--template-id',tid],capture_output=True,text=True,timeout=_stop_secs())
    except FileNotFoundError:die(3,'%s not found (CubeMaster CLI) - install it.'%exe)
    except subprocess.TimeoutExpired:die(3,'tpl delete timed out after %ds (raise CSB_STOP_WAIT)'%_stop_secs())
    if p.returncode!=0:
        blob=((p.stdout or'')+(p.stderr or'')).strip()
        die(3,'tpl rm failed: %s'%((blob[:400]if o.get('debug')else _tpl_why(blob,tid))or'(no reason given by the server)'))
    reg(c)['templates'].pop(tid,None);_TPL_DEL.add(tid);save_reg(c)
    if is_json(o):out_json({'template_id':tid,'alias':t['alias']or None})
    else:print('template %s (%s) deleted'%(t['alias']or tid,tid))
    return 0
_TPL_WL='20Gi'
ALLOW_OUT_KEEP=5
AO_SEP=re.compile('[,\uff0c;\uff1b\u3001|\\s]+')
AO_GAP=re.compile(r'^\s*[,\uff0c;\uff1b\u3001|]|[,\uff0c;\uff1b\u3001|]\s*$|[,\uff0c;\uff1b\u3001|]\s*[,\uff0c;\uff1b\u3001|]')
AO_SEP_UI=', \uff0c ; \uff1b \u3001 | or a space'
def ao_split(v):
    return[x.strip()for x in AO_SEP.split(str(v or''))if x.strip()]
def ao_check(v):
    s=str(v or'')
    if not s.strip():return[],[]
    vals=ao_split(s);prob=[]
    if AO_GAP.search(s):
        prob.append('empty entry - two separators in a row, or the list starts / ends with one')
    seen=set();dup=[]
    for x in vals:
        k=x.lower()
        if k in seen and x not in dup:dup.append(x)
        seen.add(k)
    if dup:prob.append('listed twice: %s'%', '.join(dup))
    return vals,prob
def _ao_ok_one(x):
    import ipaddress as _ip,re as _re
    x=str(x).strip().lower()
    if _re.fullmatch(r'(\*\.)?([a-z0-9-]+\.)+[a-z]{2,63}',x):
        labs=x.lstrip('*.').split('.')
        return all(l and not l.startswith('-') and not l.endswith('-') for l in labs)
    if '/' in x:
        addr,_,pl=x.partition('/')
        if not pl.isdigit():return False
    else:
        addr=x;pl=''
    try:
        if ':' in addr:
            _ip.IPv6Address(addr)
            return not pl or 0<=int(pl)<=128
        _ip.IPv4Address(addr)
        return not pl or 0<=int(pl)<=32
    except ValueError:
        return False
def _ao_is_cidr(x):
    import ipaddress as _ip
    t=str(x).strip()
    try:
        if '/' in t:_ip.ip_network(t,strict=False)
        else:_ip.ip_address(t)
        return True
    except Exception:return False
def ao_shape(vals):
    return[x for x in vals if not _ao_ok_one(x)]
def ao_shape_msg(bad):
    return('--allow-out: not a CIDR/domain: %s\n'
           'fix   example: --allow-out 10.0.0.0/8  or  --allow-out example.com  or  --allow-out *.example.com\n'
           'note  a list means ONLY those targets are allowed (csb sends deny_out 0.0.0.0/0);\n'
           '      a domain needs DNS (the whitelist default allows it)'%', '.join((bad or[])[:3]))
def _norm_allow(vals):
    return [] if list(vals or[])==['0.0.0.0/0'] else list(vals or[])
def tpl_net_kw(ao,deny,aia):
    ao=_norm_allow(ao);deny=list(deny or[]);kw={}
    if ao:kw['allow_out']=ao
    if ao and not deny and aia is not False:deny=['0.0.0.0/0']
    if deny:kw['deny_out']=deny
    if aia is not None:kw['allow_internet_access']=aia
    return kw
def _allow_out(o):
    v=o.get('allow-out')
    if v is True or(isinstance(v,str)and not v.strip()):die(2,'--allow-out needs a CIDR/domain list, or "all"')
    if v is None:return None
    s=str(v).strip().lower()
    if s in('default','all','none','no','-'):return[]
    vals,prob=ao_check(v)
    vals=[x if _ao_is_cidr(x) else x.lower() for x in vals]
    if prob:
        if prob[0].startswith('empty entry'):
            die(2,'--allow-out: empty entry (two separators in a row, or the list starts/ends with one)\n  example: 10.0.0.0/8,192.168.1.0/24')
        die(2,'--allow-out: %s\n  example: 10.0.0.0/8,192.168.1.0/24'%('; '.join(prob)))
    if not vals:die(2,'--allow-out: nothing to allow - give a CIDR/domain list, or "all"')
    bad=ao_shape(vals)
    if bad:
        die(2,ao_shape_msg(bad))
    return vals
def egress_last_get(c=None):
    try:d=prefs(c).get('egress_last')or prefs(c).get('net_combo_last')or{}
    except Exception:return None
    return d if isinstance(d,dict)and d.get('mode')else None
def resolv_servers(text):
    out=[]
    for ln in str(text or '').splitlines():
        p=ln.split()
        if len(p)>=2 and p[0]=='nameserver':out.append(p[1])
    return list(dict.fromkeys(out))
def dns_cidr(x):
    try:
        import ipaddress
        a=ipaddress.ip_address(str(x).strip().split('%')[0].strip('[]'))
    except Exception:return None
    return '%s/%d'%(a,32 if a.version==4 else 128)
def _tpl_net_get(tid,c):
    from cubesandbox import Template
    return Template.get(tid,config=sdk(c))
def tpl_net_policy(c,tid):
    try:
        import ast
        info=_tpl_net_get(tid,c);d=getattr(info,'__dict__',{})
        cr=d.get('create_request');cr=ast.literal_eval(cr)if isinstance(cr,str)else cr
        nc=((cr or{}).get('cube_network_config')or{})
        allow=list(nc.get('allowOut')or[]);deny=list(nc.get('denyOut')or[])
        dns=list(nc.get('dns')or nc.get('dnsServers')or[]);aia=nc.get('allowInternetAccess')
        if not(allow or deny or dns) and aia is None:return None
        return{'allow':allow,'deny':deny,'dns':dns,'aia':aia}
    except Exception:return None
def tpl_net_summary(p):
    if not p:return'not set'
    a=p.get('allow')or[]
    al='all'if not a else(','.join(a)if len(a)<=1 else'%d entries'%len(a))
    if not a and '0.0.0.0/0' in (p.get('deny')or[]):al='nothing (deny all)'
    return'allow %s | dns %s'%(al,'on'if p.get('dns')else('auto'if p.get('aia')is not False else'off'))
def tpl_net_lines(p):
    p=p or{}
    al=list(p.get('allow')or[]);de=list(p.get('deny')or[]);dns=list(p.get('dns')or[]);aia=p.get('aia')
    out=['internet   %s'%('on'if aia is True else'off'if aia is False else'not set (platform default: on)')]
    out+=['allow_out  %s'%(al[0]if al else'not set (platform default: all)')]+['           %s'%x for x in al[1:]]
    out+=['deny_out   %s'%(de[0]if de else'none')]+['           %s'%x for x in de[1:]]
    out+=['dns        %s'%(','.join(dns)if dns else'not stored (templates carry no DNS - start --dns-server)')]
    return out
def _pref_drop(c,key):
    p=prefs_path(c)
    try:
        with _PREFLK,_flock(p):
            d=prefs_read(c)
            if key in d:d.pop(key,None);_atomic_write(p,d)
    except Exception:pass
def egress_last_save(c,mode,ao,dns,px):
    try:save_prefs(c,egress_last={'mode':mode,'ao':list(ao or[]),'dns':bool(dns),'px':str(px or'')})
    except Exception:pass
    _pref_drop(c,'net_combo_last')
def _egress_dns_state(d):
    a=d.get('ao')or[]
    if d.get('dns'):return'on (resolver in allow list)'
    if not a or '0.0.0.0/0' in a:return'on (platform default)'
    return'off (resolver not in allow list)'
def egress_last_summary(d):
    if not d:return''
    a=d.get('ao')or[]
    st=_egress_dns_state(d);short='off'if st.startswith('off')else('on (default)'if 'platform default' in st else'on')
    return '%s | allow %s | dns %s | proxy %s'%(d.get('mode')or'on',','.join(a)if a else'all',short,d.get('px')or'none')
def egress_last_lines(d):
    if not d:return[]
    a=d.get('ao')or[]
    out=['mode     %s'%(d.get('mode')or'on'),'dns      %s'%_egress_dns_state(d),'proxy    %s'%(d.get('px')or'none')]
    if not a:out.append('allow    all (no restriction)')
    else:
        out.append('allow    %s'%a[0])
        for x in a[1:]:out.append('         %s'%x)
    return out
def allow_out_hist(c=None):
    h=prefs(c).get('allow_out_hist')or[]
    return[x for x in h if isinstance(x,str)]
def allow_out_cur(c=None):
    return list(prefs(c).get('allow_out')or[])
def allow_out_set(c,vals):
    d=prefs(c);v=[x for x in(vals or[])if x]
    h=list(d.get('allow_out_hist')or[])
    if v:
        key=','.join(v)
        h=([key]+[x for x in h if x!=key])[:ALLOW_OUT_KEEP]
    save_prefs(c,allow_out=v,allow_out_hist=h)
    return v
def allow_out_for(c,o):
    a=_allow_out(o)
    if a is None:return None
    return allow_out_set(c,a)
def proxy_hist(c=None):
    h=prefs(c).get('proxy_hist')or[]
    return[x for x in h if isinstance(x,str)]
def proxy_set(c,url):
    u=(url or'').strip();d=prefs(c)
    h=list(d.get('proxy_hist')or[])
    if u:h=([u]+[x for x in h if x!=u])
    save_prefs(c,proxy_url=u,proxy_hist=[x for x in h if isinstance(x,str)])
    return u
def proxy_hist_del(c,url):
    h=[x for x in proxy_hist(c) if x!=url]
    kw={'proxy_hist':h}
    try:
        if str(prefs(c).get('proxy_url')or'').strip()==url:kw['proxy_url']=''
    except Exception as _e:_swallow('proxy hist del',_e)
    save_prefs(c,**kw);return h
def _proxy_url(o=None):
    v=(str((o or{}).get('proxy')or'')).strip()
    if v:return v
    try:_raw=prefs().get('proxy_url')
    except Exception:_raw=None
    _pv=str(_raw or'').strip()
    if _raw is not None and not _pv:return''
    for k in('https_proxy','HTTPS_PROXY','http_proxy','HTTP_PROXY','all_proxy','ALL_PROXY'):
        v=(os.environ.get(k)or'').strip()
        if v:return v
    return _pv
def _host_lan_ip():
    import socket as _s
    try:
        u=_s.socket(_s.AF_INET,_s.SOCK_DGRAM);u.connect(('10.255.255.255',1))
        ip=u.getsockname()[0];u.close()
        if ip and not ip.startswith('127.'):return ip
    except Exception:pass
    return''
def _proxy_host_cidr(pe):
    try:
        from urllib.parse import urlsplit
        h=urlsplit((pe or{}).get('HTTP_PROXY')or'').hostname
    except Exception:return''
    if not h:return''
    return('%s/128'%h)if':'in h else('%s/32'%h)

def _internal_cidrs():
    """Extra CIDRs that belong to the cluster: off the proxy, opened with it.

    Empty unless `CSB_INTERNAL_CIDR` lists them (comma separated), so no private
    subnet has to be baked into the source."""
    v=(os.environ.get('CSB_INTERNAL_CIDR')or'').strip()
    return[c for c in re.split(r'[\s,]+',v)if c]

def _auto_proxy_env(o=None):
    if not _sw('auto_proxy'):return{}
    raw=_proxy_url(o)
    if not raw:return{}
    try:
        from urllib.parse import urlsplit
        u=urlsplit(raw if'://'in raw else'http://'+raw)
        h=(u.hostname or'').strip();p=u.port or 7897
    except Exception:return{}
    if not h or not p:return{}
    if h in('127.0.0.1','localhost','::1','0.0.0.0'):
        h=_host_lan_ip()
        if not h:return{}
    url='http://%s:%d'%(h,p)
    no=','.join(['localhost','127.0.0.1','::1','169.254.0.0/16']+_internal_cidrs())
    return{'HTTP_PROXY':url,'HTTPS_PROXY':url,'http_proxy':url,'https_proxy':url,'NO_PROXY':no,'no_proxy':no}
def _swallow(where,exc=None):
    if not os.environ.get('CSB_DEBUG'):
        return
    try:
        sys.stderr.write('csb: ignored %s error: %s\n'%(where,exc))
    except Exception:
        pass
NET_MODES=('on','off')
_ALIAS_NET={'auto':'on','custom':'on','1':'on','0':'off'}
def net_mode(o,default=None):
    v=o.get('net')
    if v in(None,True,''):v=None
    if v is None and o.get('no-net'):return'off'
    if v is None:
        d=str(default or'on').lower()
        return _ALIAS_NET.get(d,d)
    v=str(v).strip().lower()
    v=_ALIAS_NET.get(v,v)
    if v not in NET_MODES:die(2,'--net wants on or off (got %r)\n'
        '      on  = allow internet; also give --allow-out <cidr|domain>[, ...] or --proxy <url>\n'
        '      off = no network at all'%v)
    return v
def _net_pol(auto_pe,ao,o,default=None):
    mode=net_mode(o,default)
    if mode=='off':return []
    ph=_proxy_host_cidr(auto_pe)if auto_pe else''
    ic=_internal_cidrs()
    if ao is not None:
        return list(dict.fromkeys(list(ao)+([ph]+ic if ph else[])))
    if ph:
        return list(dict.fromkeys([ph,'0.0.0.0/0']+ic))
    return []
def _net_deny(ao):
    return['0.0.0.0/0']if ao else[]
def _sbx_get(c,sid):
    try:return dict((prefs(c).get('sbx')or{}).get(sid)or{})
    except Exception:return {}
def _live_ids_full(c):
    try:
        raw,full,_why=_sb_list(c)
    except Exception:
        return None
    if raw is None or not full:
        return None
    return {r.get('sandboxID') for r in raw if r.get('sandboxID')}
def _sbx_prune(c,live):
    if live is None:return 0
    try:
        d=dict(prefs(c).get('sbx')or{})
        live=set(live)
        try:ent=set(reg(c)['entries'])
        except Exception:ent=set()
        drop=[k for k in d if k not in live and k not in ent]
        if not drop:return 0
        for k in drop:d.pop(k,None)
        save_prefs(c,sbx=d)
        return len(drop)
    except Exception as _e:
        _swallow('sbx prune',_e);return 0
_SB_FULL=[None]
def _sweep_cooldown():
    try:return max(0,int(_sw('sbx_sweep_cooldown')))
    except Exception:return 600
def _sweep_path(c):
    return os.path.join(os.path.dirname(os.path.abspath(c['reg'])),'.sbx-sweep.json')
def _sweep_load(c):
    try:
        with open(_sweep_path(c),encoding='utf-8')as f:d=json.load(f)
        return d if isinstance(d,dict)else{}
    except Exception:return{}
def _sweep_save(c,d):
    try:
        q=_sweep_path(c);t=q+'.tmp'
        with open(t,'w',encoding='utf-8')as f:json.dump(d,f)
        os.replace(t,q)
    except Exception as _e:_swallow('sbx sweep',_e)
def _sbx_sweep(c,live):
    if live is None:return 0
    if not _sw('sbx_sweep'):return 0
    try:
        st=_sweep_load(c);susp=dict(st.get('suspects')or{})
        now=time.time();drop=[]
        d=dict(prefs(c).get('sbx')or{})
        ent=reg(c)['entries']
        for k in list(d):
            if k in live or k in ent:susp.pop(k,None);continue
            first=susp.get(k)
            try:first=float(first)
            except Exception:first=None
            if first is None:susp[k]=now;continue
            if now-first>=_sweep_cooldown():drop.append(k);susp.pop(k,None)
        if not drop:
            if susp:_sweep_save(c,{'suspects':susp})
            else:
                try:os.unlink(_sweep_path(c))
                except Exception:pass
            return 0
        for k in drop:d.pop(k,None)
        save_prefs(c,sbx=d);_sweep_save(c,{'suspects':susp})
        return len(drop)
    except Exception as _e:
        _swallow('sbx sweep',_e);return 0
def _save_sbxenv(c,sid,envs,mode=None,pol=None,deny=None,dns=None,ts=None):
    try:
        d=dict(prefs(c).get('sbx')or{})
        rec=dict(d.get(sid)or{})
        _pxk=('http_proxy','https_proxy','all_proxy','no_proxy')
        rec['env']={str(k):str(v)for k,v in(envs or{}).items()
                    if str(k).lower()not in _pxk}
        if mode:rec['mode']=mode
        if pol is not None:rec['pol']=list(pol)
        if deny is not None:rec['deny']=list(deny)
        if dns is not None:rec['dns']=list(dns)
        if ts:rec['net_ts']=ts
        d[sid]=rec
        kw={'sbx':d}
        if mode and mode!='template':kw['net_choice']=mode
        save_prefs(c,**kw)
    except Exception as _e:_swallow('sbx env',_e)
def _sbx_drop(c,sid):
    try:
        d=dict(prefs(c).get('sbx')or{})
        if sid in d:
            d.pop(sid,None);save_prefs(c,sbx=d)
    except Exception as _e:_swallow('sbx drop',_e)
def sbx_net_pol(c,sid):
    return list(_sbx_get(c,sid).get('pol')or[])
def _saved_sbxenv(c,sid):
    return dict(_sbx_get(c,sid).get('env')or{})
def sbx_net_saved(c,sid):
    return _sbx_get(c,sid).get('mode')
def sbx_net_deny(c,sid):
    return list(_sbx_get(c,sid).get('deny')or[])
def sbx_net_mode(c,sid):
    return _sbx_get(c,sid).get('mode') or (prefs(c).get('net_choice')if hasattr(prefs(c),'get')else None) or'on'
def exec_envs(c,o,sid=None):
    d=_saved_sbxenv(c,sid)if sid else {}
    mode=sbx_net_mode(c,sid)if sid else net_mode(o)
    _pe=_auto_proxy_env()if mode!='off'else{}
    if _pe and not any(str(k).lower()in('http_proxy','https_proxy','all_proxy')for k in _env_pairs(o)):
        d={**_pe,**d}
    d.update(_env_pairs(o))
    return d
def _tpl_sz(v,what):
    if v in(None,True,''):return None
    m=re.fullmatch(r'(\d+)\s*([KMGT])?(i?)[Bb]?',str(v).strip(),re.I)
    if not m:die(2,'tpl build: --%s wants a size like 1G / 500M / 20Gi / 10240 (=MB)'%what)
    n=int(m.group(1));u=(m.group(2)or'M').upper()
    return{'K':max(1,n//1024),'M':n,'G':n*1024,'T':n*1024*1024}[u]
def _tpl_res(cpu,mem):
    if cpu is None and mem is None:return None,None,''
    n=[]
    if cpu is None:cpu,=1000,;n.append('--cpu 1000 (= 1 core, paired default)')
    if mem is None:mem,=1024,;n.append('--mem 1024M (paired default)')
    return cpu,mem,('' if not n else'note: cpu and memory are a pair on the server - filled in %s'%', '.join(n))
def cmd_tpl_build(o,c):
    img=o.get('image');al=o.get('alias')
    if not img:die(2,'tpl build: --image <ref> --alias <NAME> takes --disk/--mem/--cpu/--allow-out')
    if not al:die(2,'tpl build: --alias required (no auto-name; e.g. mini4)')
    ae=alias_err(al)
    if ae:die(2,ae)
    if o.get('dns-server'):die(2,'tpl build does not take --dns-server - DNS is a start-time flag (csb start ... --dns-server <ip>)')
    _dsk=_tpl_sz(o.get('disk'),'disk');_mem=_tpl_sz(o.get('mem'),'mem')
    _cpu=None
    if o.get('cpu')not in(None,True,''):_cpu=_int(o.get('cpu'),1000,'--cpu')
    if _cpu is not None and _cpu<1:die(2,'tpl build: --cpu >= 1 millicore (omit for the default)')
    if _dsk is not None and _dsk<1:die(2,'tpl build: --disk >= 1 MiB (omit for the default)')
    if _mem is not None and _mem<1:die(2,'tpl build: --mem >= 1 MiB (omit for the default)')
    _own=alias_taken(c,'',al)
    if _own:alias_clash_die(al,_own,'tpl build')
    _cpu,_mem,_rn=_tpl_res(_cpu,_mem)
    _ao=_allow_out(o)
    _deny=[]
    for x in (list(o.get('deny-out')or[]) if isinstance(o.get('deny-out'),list) else ([o.get('deny-out')] if o.get('deny-out') else [])):
        for y in str(x).replace(' ','').split(','):
            if not y:continue
            if not _ao_is_cidr(y):die(2,'tpl build --deny-out: not a CIDR: %s'%y)
            _deny.append(y)
    _aia=False if o.get('no-internet') else None
    if _aia is False and o.get('allow-out') is not None:die(2,'tpl build --no-internet conflicts with --allow-out - choose one')
    for x in (_ao or []):
        if not _ao_is_cidr(x):die(2,'tpl build --allow-out only takes CIDR (templates carry no DNS; use start --allow-out <domain> instead)')
    dry_only(o,'build template %s from %s'%(al,img),why='building the template %s'%al)
    disk='%dMi'%_dsk if _dsk else _TPL_WL
    import time as _t
    if not is_json(o):err('building template %s from %s'%(al,img))
    if _rn and not is_json(o):err(_rn)
    _kw=dict(image=img,name=al,writable_layer_size=disk,cpu_count=_cpu,memory_mb=_mem)
    _kw.update(tpl_net_kw(_ao,_deny,_aia))
    try:tb=_Template().build(config=sdk(c),**_kw)
    except Exception as ex:die(3,'build failed: %s (registry must be CN-reachable)'%ex)
    bid=getattr(tb,'build_id',None) or getattr(tb,'job_id','') or ''
    tid=getattr(tb,'template_id',None) or ''
    st='';msg=''
    for i in range(150):
        try:
            if tid and bid:
                bs=_Template().get_build_status(tid,bid,config=sdk(c))
                st=bs.status or '';tid=tid or bs.template_id;msg=bs.error_message or bs.message or ''
        except Exception:
            pass
        if st.upper() not in('READY','SUCCEEDED','FAILED','ERROR'):
            row=next((t for t in tpl_rows(c) if t['alias']==al),None)
            if row:st=row['status'] or st;tid=row['id']
        if not is_json(o):
            if not _sw('auto_no_spin'):sys.stderr.write('\r   build %s: waited %ds   '%(st or 'submitted',(i+1)*2));sys.stderr.flush()
        if st.upper() in('READY','SUCCEEDED','FAILED','ERROR'):break
        _t.sleep(2)
    else:
        if not is_json(o):sys.stderr.write('\n')
        die(3,'tpl build timeout: job %s still running (check: cubemastercli %s tpl build-status)'%(bid,cm_txt()))
    if not is_json(o):sys.stderr.write('\n')
    if st.upper() in('FAILED','ERROR'):die(3,'template build %s: %s (alias %s; see cubemastercli tpl build-status --job-id %s)'%(st.upper(),msg or 'server error',al,bid))
    if is_json(o):out_json({'template_id':tid or None,'alias':al,'job_id':bid or None,'status':st})
    else:print('%s %s READY'%(tid or al,al))
    return 0
def _auth_hdrs(c):
    return{'X-API-Key':c['key']} if c['key'] else {}
def _get_json(c,path):
    import requests
    r=requests.get(c['api']+path,headers=_auth_hdrs(c),timeout=_http_secs())
    if r.status_code==404:return None
    r.raise_for_status();return r.json()
def exec_labels(o):
    return [x for x in (o.get('_') or []) if x]
def _exec_cmd(tail):
    import shlex as _sh
    if isinstance(tail,list) and len(tail)>=3 and str(tail[0]).rsplit('/',1)[-1] in('sh','bash','dash','zsh','ash') and str(tail[1])=='-c':
        c='%s -c %s'%(tail[0],_sh.quote(' '.join(str(x) for x in tail[2:])))
    else:
        c=' '.join(str(x) for x in tail) if isinstance(tail,list) else str(tail)
    if not c.strip():die(2,'exec: empty command (e.g. csb exec <id> -- ls /tmp)')
    return c
def _env_pairs(o,what='exec'):
    d={}
    for x in _m(o,'env'):
        k,v=_kv(x,'--env')
        if not str(k).strip():die(2,'%s: --env needs a name before "=" (got %r)'%(what,x))
        d[str(k).strip()]=str(v)
    return d
_EXEC_STREAM_MAX=64*1048576
SHELL_MAX_DEFAULT=64*1024*1024
def shell_max():
    v=(os.environ.get('CSB_SHELL_MAX')or'').strip()
    if v:
        m=re.fullmatch(r'(\d+)\s*([KMG])?',v,re.I)
        return int(m.group(1))*{'':1,'K':1024,'M':1024**2,'G':1024**3}[(m.group(2)or'').upper()] if m else SHELL_MAX_DEFAULT
    try:return int(_sw('shell_max'))
    except Exception:return SHELL_MAX_DEFAULT
def shell_limit_hit(total,cap,warned):
    return bool((not warned)and total>cap)
def _exec_guard(cmd,cap=None):
    cap=cap or _EXEC_STREAM_MAX
    return ('__csb_o=$(mktemp 2>/dev/null || echo /tmp/.csb-exec-o-$$); '
            '__csb_e=$(mktemp 2>/dev/null || echo /tmp/.csb-exec-e-$$); '
            '{ %s\n} >"$__csb_o" 2>"$__csb_e"; __csb_rc=$?; '
            '__csb_n=$(( $(wc -c <"$__csb_o") + $(wc -c <"$__csb_e") )); '
            'if [ "$__csb_n" -gt %d ]; then echo "CSB_OUT_TOO_BIG $__csb_n" >&2; '
            'rm -f "$__csb_o" "$__csb_e"; exit 97; fi; '
            'cat "$__csb_o"; cat "$__csb_e" >&2; rm -f "$__csb_o" "$__csb_e"; exit $__csb_rc')%(cmd,cap)
def _exec_guard_hit(r):
    e=(getattr(r,'stderr','')or'').lstrip()
    if not e.startswith('CSB_OUT_TOO_BIG '):return None
    for tok in e.split():
        if tok.isdigit():return int(tok)
    return 0
def _exec_big(n,limit,fix):
    return('exec: output is %s - too large to print safely\n'
           'why   one streamed reply holds the whole output in RAM; the limit is %s\n'
           'fix   %s'%(_cp_size(n),_cp_size(limit),fix))
def _exec_guard_msg(n,label,out=None):
    return _exec_big(n,_EXEC_STREAM_MAX,
        'csb exec %s --out /tmp/out -- <cmd>   then   csb cp %s:/tmp/out ./'%(label,label))
def _exec_bulk(labels,cmd,c,o,envs=None):
    _n=len(labels);ok=0;bad=0;lim=_exec_secs()
    _xkw={'envs':envs}if envs else {}
    for i,label in enumerate(labels,1):
        sb,_=_find_sb(label,c)
        if not sb:
            bad+=1;err('exec %s: %s'%(label,_sbnope(label,c)));continue
        st=(sb or{}).get('state')
        if st in('paused','pausing'):
            bad+=1;err('exec %s: it is %s - resume it first:  csb resume %s --yes'%(label,st,sb['id']));continue
        print('== %d/%d %s'%(i,_n,label))
        _cmd=cmd if o.get('out')else _exec_guard(cmd)
        _res,_j=_watch(o,'running the command in %s'%label,lambda:_inst(sb,c).commands.run(_cmd,timeout=lim,**_xkw),lim)
        _ex=_re(_j)
        if _res!='ok':
            bad+=1;err('exec %s: no answer for %ds (raise it: CSB_EXEC_WAIT)'%(label,int(lim)));continue
        if _ex is not None:
            bad+=1;err('exec %s failed: %s'%(label,_ex));continue
        r=_j['box'].get('val')
        _gn=_exec_guard_hit(r)
        if _gn is not None:
            bad+=1;err('exec %s: output too large (%s) - use --out, one sandbox at a time'%(label,_cp_size(_gn)));continue
        if _exec_out_size(r)>_EXEC_OUT_MAX:
            bad+=1;err('exec %s: output %s - skipped (use --out)'%(label,_cp_size(_exec_out_size(r))));continue
        if r.stdout:sys.stdout.write(r.stdout if r.stdout.endswith('\n') else r.stdout+'\n')
        if r.stderr:sys.stderr.write(r.stderr if r.stderr.endswith('\n') else r.stderr+'\n')
        if r.exit_code not in(0,None):
            bad+=1;err('exec %s: remote exit code %d'%(label,r.exit_code))
        else:ok+=1
    print('bulk exec: %d of %d sandboxes ok'%(ok,_n))
    return 1 if bad else 0
_EXEC_OUT_MAX=64*1048576
def _exec_out_too_big(n,label,out):
    _fix=('the file was written:  csb cp %s:%s ./'%(label,out))if out else(
        'csb exec %s --out /tmp/out -- <cmd>   then   csb cp %s:/tmp/out ./'%(label,label))
    die(2,_exec_big(n,_EXEC_OUT_MAX,_fix))
def _exec_out_size(r):
    return len(r.stdout or'')+len(r.stderr or'')
def cmd_exec(o,c):
    labs=exec_labels(o)
    _eu='exec: <id> -- <cmd>\n       example: csb exec <sandbox-id> -- ls /tmp'
    if not labs:die(2,_eu)
    tail=o.get('tail')
    if not tail:die(2,_eu)
    if o.get('dry-run'):die(2,'exec --dry-run: nothing sent; drop it to run\n      (argv preview: the bulk commands\' --list)')
    if len(labs)>1:
        if o.get('o')=='json':
            die(2,'exec: bulk over %d labels is text-only (-o json is per sandbox; run labels one by one)'%len(labs))
        return _exec_bulk(labs,_exec_cmd(tail),c,o,exec_envs(c,o))
    label=labs[0]
    sb,_=_find_sb(label,c)
    if not sb:die(2,_sbnope(label,c))
    _need_run(sb,'csb exec')
    cmd=_exec_cmd(tail)
    _xenv=exec_envs(c,o,sb['id'])
    _xkw={'envs':_xenv}if _xenv else {}
    _out=o.get('out')
    if _out:cmd='{ %s\n} > %s 2>&1'%(cmd,_shlex.quote(_out))
    else:cmd=_exec_guard(cmd)
    lim=_exec_secs()
    _res,_j=_watch(o,'running the command in %s'%label,lambda:_inst(sb,c).commands.run(cmd,timeout=lim,**_xkw),lim)
    _ex=_re(_j)
    if _res!='ok':
        die(1 if _res=='stop'else 3,'exec %s: %s (CSB_EXEC_WAIT); still running inside\n'
            'fix   csb int %s --list  /  csb int %s -- <pattern>'%(
                label,'stopped watching'if _res=='stop'else'no answer for %ds'%int(lim),label,label))
    if _ex is not None:die(3,'exec failed: %s'%_ex)
    r=_j['box'].get('val')
    _gn=_exec_guard_hit(r)
    if _gn is not None:die(2,_exec_guard_msg(_gn,label))
    if _out:
        _sz=None
        try:_sz=_fs(sb,c).stat(_out).get('size')
        except Exception:pass
        if is_json(o):
            out_json({'exit_code':r.exit_code,'out':_out,'bytes':int(_sz)if _sz else None})
        else:
            print('wrote %s:%s  (%s)'%(label,_out,_cp_size(int(_sz))if _sz else'?'))
            print('  read it back:  csb cp %s:%s ./'%(label,_out))
        return 3 if r.exit_code not in(0,None) else 0
    if _exec_out_size(r)>_EXEC_OUT_MAX:_exec_out_too_big(_exec_out_size(r),label,None)
    if is_json(o):
        out_json({'exit_code':r.exit_code,'stdout':r.stdout,'stderr':r.stderr})
        return 3 if r.exit_code not in(0,None) else 0
    if r.stdout:sys.stdout.write(r.stdout if r.stdout.endswith('\n') else r.stdout+'\n')
    if r.stderr:sys.stderr.write(r.stderr if r.stderr.endswith('\n') else r.stderr+'\n')
    if r.exit_code not in(0,None):err('remote exit code %d'%r.exit_code);return 3
    return 0
def cmd_int(o,c):
    label=need_arg(o,'int: <id> [-- pattern]\n  no pattern = list what runs inside the sandbox\n  the sandbox own envd / jupyter services need --force (signalling them breaks that sandbox)')
    sb,_=_find_sb(label,c)
    if not sb:die(2,_sbnope(label,c))
    _need_run(sb,'csb int')
    import shlex as _sh
    pat=(o.get('tail')or[])
    pat=' '.join(str(x) for x in pat) if isinstance(pat,list)else str(pat or'')
    if o.get('tail')is not None and not pat.strip()and not o.get('list'):
        die(2,'int: nothing after --; give the pattern:  csb int %s -- node'%label)
    if o.get('dry-run'):die(2,'int: nothing to preview\nfix   csb int <id> --list')
    sg=str(o.get('sig')or'TERM').upper().replace('SIG','')
    if sg not in('TERM','KILL','HUP','INT','QUIT','9','15','1'):die(2,'int: --sig wants TERM / KILL / HUP / INT / QUIT (default TERM)')
    kill=bool(pat.strip())and not o.get('list')
    if not pat.strip()and not o.get('list'):
        kill=False
    sc=("_p=%s; for d in /proc/[0-9]*; do p=${d#/proc/}; [ \"$p\" = \"$$\" ] && continue; [ \"$p\" = 1 ] && continue; "
        "c=$(tr '\\0' ' ' < \"$d/cmdline\" 2>/dev/null) || continue; [ -z \"$c\" ] && continue; case \"$c\" in *cmdline*) continue;; esac; "
        "case \"$c\" in *envd\\ -port*|*jupyter-server*|*ipykernel_launcher*) [ %s = 1 ] || { echo \"SKIP $p platform service: $c\"; continue; };; esac; "
        "case \"$c\" in *${_p}*) if [ %s = 1 ]; then kill -%s \"$p\" 2>/dev/null && echo \"SENT %s $p $c\"; else echo \"HIT $p $c\"; fi;; esac; done")%(
        _sh.quote(pat)if pat.strip()else"''",'1'if o.get('force')else'0','1'if kill else'0',sg,sg)
    try:r=_inst(sb,c).commands.run(sc)
    except Exception as ex:die(3,'int failed: %s'%ex)
    out=(r.stdout or'').strip();lines=[x for x in out.split('\n')if x.strip()]
    if is_json(o):
        out_json({'sandbox_id':sb['id'],'pattern':pat,'signal':sg if kill else None,
                  'matches':[x[4:]for x in lines if x.startswith('HIT ')],
                  'signaled':[x[5:]for x in lines if x.startswith('SENT ')]})
        return 0
    if not lines:
        print('nothing in %s matches %r'%(sb.get('label')or label,pat)if pat.strip()
              else 'no other process is running inside %s'%(sb.get('label')or label))
        if (r.stderr or'').strip():err(r.stderr.strip()[:200])
        return 0
    for x in lines:print(x)
    if kill:err('sent SIG%s to %d process(es) - the sandbox shell comes back with its prompt'%(sg,len([x for x in lines if x.startswith('SENT ')])))
    else:err('that is what is running right now; pass a pattern to signal one:  csb int %s -- <pattern>'%(sb.get('label')or label))
    return 0
_DROP=('ts','time','timestamp','level','severity')
def _unwrap(t):
    raw=str(t or '')
    j=None
    st=raw.strip()
    if st.startswith('{') and st.endswith('}'):
        try:j=_json.loads(st)
        except Exception:j=None
    if isinstance(j,dict):
        for k in('msg','message','line','log'):
            if k in j:
                body=str(j.get(k) or '')
                extra=[(kk,vv)for kk,vv in j.items()if kk not in _DROP and kk not in('msg','message','line','log')]
                break
        else:
            body=''
            extra=[(kk,vv)for kk,vv in j.items()if kk not in _DROP]
        if extra:
            body=(body+'  'if body else'')+'  '.join('%s=%s'%(kk,vv)for kk,vv in extra)
        return body.strip()
    m=re.search(r'\bmsg=(?:"([^"]*)"|(\S+))',st)
    if m and re.match(r'^\s*[\w.]+=',st):
        return(m.group(1)or m.group(2)or'').strip()
    return raw

def _logtxt(it):
    if isinstance(it,dict):return str(it.get('line') or it.get('msg') or it.get('message') or _json.dumps(it))
    return str(it)
def _loglv(it):
    lv=str((it.get('level')if isinstance(it,dict)else'')or'').strip().lower()
    return lv.upper()if lv and lv!='info'else''
def _logfl(it):
    f=it.get('fields')if isinstance(it,dict)else None
    if not isinstance(f,dict)or not f:return''
    return'  '+' '.join('%s=%s'%(k,_cln(f[k]))for k in list(f)[:6])
def _logts(it):
    t=it.get('timestamp')if isinstance(it,dict)else None
    return _disp(t)if t else''
def _get_logs_pages(c,sb,n):
    import urllib.parse as _up
    items=[];tok=None;pages=0;body=None
    while pages<20:
        q='/sandboxes/%s/logs'%sb['id']
        if tok:q+='?nextToken=%s'%_up.quote(str(tok),safe='')
        b=_get_json(c,q)
        if b is None:
            if body is None:return None
            break
        body=b if body is None else body
        chunk=(b.get('logs') if isinstance(b,dict) else b)or[]
        if isinstance(b,dict)and not chunk and b.get('logEntries'):chunk=b['logEntries']
        items=chunk+items
        tok=(b.get('nextToken') if isinstance(b,dict)else None)
        pages+=1
        if not tok or len(items)>=n:break
    if body is None:return None
    d=dict(body) if isinstance(body,dict)else{'logs':items}
    d['logs']=items
    d['nextToken']=tok
    return d
def cmd_logs(o,c):
    label=need_arg(o,'logs: <id> [N]');n=_int(o['_'][1] if len(o['_'])>1 else None,200,'N')
    if n<1:die(2,'logs N must be >=1, got %d'%n)
    sb,_=_find_sb(label,c)
    if not sb:die(2,_sbnope(label,c))
    body=_get_logs_pages(c,sb,n)
    if body is None:
        if is_json(o):out_json({'sandbox_id':sb['id'],'logs':[],'nextToken':None,'note':'no logs (404)'})
        else:print('(no logs - the server has none for this sandbox yet; it may still be starting)')
        return 0
    items=body.get('logs',[]) if isinstance(body,dict) else body
    if isinstance(body,dict)and not items and body.get('logEntries'):items=body['logEntries']
    allf=bool(o.get('all'))
    if not allf:
        def _noise(it):
            t=_logtxt(it)
            if'time_sync'in t or'ptp'in t or'system time behind'in t:return True
            return not _unwrap(t).strip()
        mf=[it for it in items if not _noise(it)]
        if len(mf)<len(items)and not is_json(o):err('WARN: %d clock noise line(s) filtered (logs --all for full)'%(len(items)-len(mf)))
        items=mf
    if is_json(o):
        d=dict(body) if isinstance(body,dict) else {'logs':items}
        d['sandbox_id']=sb['id'];d['logs']=items
        d.setdefault('nextToken',None);d.setdefault('note',None)
        out_json(d);return 0
    if not items:print('(no logs - nothing left after filtering the clock noise; --all shows the raw lines)');return 0
    W=_termw()
    for it in items[-n:]:
        _t=_cln(_logtxt(it))if allf else _cln(_unwrap(_logtxt(it)))
        _tprint(' '.join(x for x in(_logts(it),_loglv(it),_t)if x)+_logfl(it),'  ',W)
    return 0
_SKIP_DIRS={'.git','.svn','.hg','__pycache__'};_SKIP_SUF=('.pyc','.pyo','.tmp')
def _split_obj(o,arg):
    if ':' in arg:
        l,p=arg.split(':',1);return l,p or '/'
    return arg,'/'
def _obj_only(o,cmd,usage):
    if len(o.get('_')or[])>1:
        die(2,'%s: one object only - the path belongs after the colon\n  fix   csb %s <id>:<path>'%(cmd,cmd))
    return need_arg(o,usage)
def _need_run(sb,what):
    st=(sb or{}).get('state')
    if st not in('paused','pausing'):return
    _l=(sb or{}).get('label')or(sb or{}).get('id')or'?'
    _i=(sb or{}).get('id')or _l
    if st=='pausing':die(3,'%s is pausing - %s needs a running sandbox\n  wait  the pause is still being applied; csb info %s shows it'%(_l,what,_i))
    die(3,'%s is %s - %s needs a running sandbox\n  fix   csb resume %s --yes'%(_l,st,what,_i))
def _fs(sb,c):
    _need_run(sb,'this file command')
    return _inst(sb,c).files
import shlex as _shlex
_B_MIN=8*1048576
def _cp_route(o,size):
    via=str(o.get('via')or'').strip().lower()
    if via in('http','files'):return via
    return 'http' if size is not None and int(size)>=_B_MIN else'files'
def _cp_size(n):
    n=int(n)
    if n>=1073741824:return '%.2f GiB'%(n/1073741824.0)
    if n>=1048576:return '%.1f MiB'%(n/1048576.0)
    if n>=1024:return '%d KiB'%(n//1024)
    return '%d bytes'%n
_B_SRV=r"""import http.server,socketserver,os
F=os.environ['F'];T=os.environ.get('T','');UP=os.environ.get('UP')=='1'
class H(http.server.BaseHTTPRequestHandler):
    def _tok(self):return (not T)or('t='+T)in self.path
    def _len(self,n):
        self.send_response(200);self.send_header('Content-Length',str(n));self.end_headers()
    def do_HEAD(self):
        if not self._tok():self.send_error(403);return
        if not os.path.isfile(F):self.send_error(404);return
        self.send_response(200);self.send_header('Content-Length',str(os.path.getsize(F)));self.end_headers()
    def do_GET(self):
        if not self._tok():self.send_error(403);return
        if not os.path.isfile(F):self.send_error(404);return
        self._len(os.path.getsize(F))
        with open(F,'rb') as f:
            while True:
                b=f.read(1048576)
                if not b:break
                self.wfile.write(b)
    def do_PUT(self):
        if not self._tok():self.send_error(403);return
        n=int(self.headers.get('Content-Length')or 0);got=0
        with open(F,'wb') as f:
            while got<n:
                b=self.rfile.read(min(1048576,n-got))
                if not b:break
                f.write(b);got+=len(b)
        self._len(0);self.wfile.write(str(got).encode())
    def log_message(self,*a):pass
socketserver.TCPServer.allow_reuse_address=True
socketserver.TCPServer(('0.0.0.0',int(os.environ['P'])),H).serve_forever()
"""
_B_SCRIPT='/tmp/.csb-b.py'
def _b_ready(sb,c):
    try:r=_inst(sb,c).commands.run('command -v python3 >/dev/null 2>&1 && echo yes',timeout=25)
    except Exception:return False
    return 'yes' in (r.stdout or '')
def _b_serve(sb,c,sl,path,up=False):
    import secrets,random,time
    if not _b_ready(sb,c):
        raise RuntimeError('the guest has no python3 - cannot start the one-file server')
    tok=secrets.token_hex(8);port=0;url=None
    _fs(sb,c).write_files([(_B_SCRIPT,_B_SRV.encode())])
    for _try in range(6):
        port=random.randint(20000,60000)
        cmd=('python3 -c "import subprocess,sys;subprocess.Popen([sys.executable,%r],'
             'stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,'
             'stdin=subprocess.DEVNULL,start_new_session=True)"'%_B_SCRIPT)
        try:r=_inst(sb,c).commands.run(cmd,envs={'F':path,'P':str(port),'T':tok,'UP':'1'if up else'0'},timeout=25)
        except Exception as ex:raise RuntimeError('could not start the server (%s)'%ex)
        if r.exit_code not in(0,None):raise RuntimeError('the guest refused to start the server: %s'%((r.stderr or'').strip()[:160]))
        time.sleep(0.6)
        try:
            host=_inst(sb,c).get_host(port)
            cand='%s?t=%s'%(_url_of(host),tok)
        except Exception:
            continue
        try:
            import requests
            with requests.get(cand,timeout=5,stream=True,allow_redirects=False) as _r:
                code=_r.status_code
            if code<500:url=cand;break
        except Exception:
            continue
    if not url:raise RuntimeError('the one-file server did not come up on any port')
    err('note: the file is served on the sandbox public port for this copy only (token %s)'%tok[:6])
    return url,port
def _b_stop(sb,c):
    try:_inst(sb,c).commands.run("pkill -f '%s' >/dev/null 2>&1; rm -f '%s'"%(_B_SCRIPT,_B_SCRIPT),timeout=20)
    except Exception:pass
def _cp_get_http(sb,c,sl,path,local,size):
    import requests
    url,_port=_b_serve(sb,c,sl,path,up=False)
    tmp=local+'.csbpart'
    try:
        with requests.get(url,stream=True,timeout=(10,600)) as r:
            if r.status_code!=200:raise RuntimeError('the guest answered %s'%r.status_code)
            got=0
            with open(tmp,'wb') as f:
                for ch in r.iter_content(1048576):
                    f.write(ch);got+=len(ch)
        if size is not None and got!=int(size):
            raise RuntimeError('got %d bytes, not %d'%(got,int(size)))
        os.replace(tmp,local)
    finally:
        try:
            if os.path.exists(tmp):os.remove(tmp)
        except Exception as _e:_swallow('cp http',_e)
        _b_stop(sb,c)
def _cp_put_http(sb,c,sl,path,local,size):
    import requests
    url,_port=_b_serve(sb,c,sl,path,up=True)
    try:
        with open(local,'rb') as f:
            r=requests.put(url,data=f,timeout=(10,600))
        if r.status_code!=200:raise RuntimeError('the guest answered %s'%r.status_code)
        n=str(r.text or '').strip()
        if n.isdigit()and size is not None and int(n)!=int(size):
            raise RuntimeError('the guest wrote %s of %s bytes'%(n,size))
    finally:_b_stop(sb,c)

def _cp_envd_stream(sb,c,path,local,size):
    import requests as _rq
    fs=_fs(sb,c);fs._ensure_client()
    url='http://%s/files'%fs._sandbox.get_host(49983)
    tmp=local+'.csbpart';got=0
    with _rq.get(url,params={'path':path,'username':'root'},headers=fs._base_headers(),stream=True,timeout=(10,900)) as r:
        if r.status_code!=200:raise RuntimeError('envd answered %s'%r.status_code)
        with open(tmp,'wb') as f:
            for ch in r.iter_content(1048576):
                f.write(ch);got+=len(ch)
    if size is not None and got!=int(size):
        try:os.remove(tmp)
        except Exception as _e:_swallow('cp stream',_e)
        raise RuntimeError('stream gave %d bytes, not %d'%(got,int(size)))
    os.replace(tmp,local)
def _cp_slices(sb,c,sl,tgt,local,size):
    fs=_fs(sb,c);inst=_inst(sb,c);part=16*1048576;idx=0;blobs=[]
    tok=os.urandom(4).hex()
    with open(local,'rb') as fh:
        while True:
            b=fh.read(part)
            if not b:break
            blobs.append(('/tmp/.csb-p%s-%d'%(tok,idx),b));idx+=1
    fs.write_files(blobs)
    names=' '.join(p for p,_ in blobs)
    r=inst.commands.run('cat %s > %s && rm -f %s'%(names,_shlex.quote(tgt),names),timeout=900)
    if r.exit_code not in(0,None):
        try:inst.commands.run('rm -f %s'%names,timeout=_stop_secs())
        except Exception as _e:_swallow('cp slices',_e)
        raise RuntimeError('the merge failed: %s'%((r.stderr or'').strip()[:160] or r.exit_code))
def _cp_envd_guard(o,size,ex=None,up=False):
    _big=size is not None and int(size)>=_B_MIN
    if not _big and ex is None:return
    if up:
        _msg='16 MiB slices can still hit 413. Continue?'
        if not confirm(o,_msg,why='uploading in 16 MiB slices (risky for big files)'):
            die(2,'cp aborted; nothing copied. Use a volume or exec --out.')
    else:
        _msg='envd keeps the file in RAM and cannot release it. Continue?'
        if not confirm(o,_msg,why='copying over the envd stream (risky for big files)'):
            die(2,'cp aborted; nothing copied. Use a volume or exec --out.')

def _cp_get(sb,c,o,sl,sp,local,size):
    via=_cp_route(o,size)
    _pex=None
    if via=='http':
        try:
            _val(o,'fetching %s:%s over the sandbox port'%(sl,sp),lambda:_cp_get_http(sb,c,sl,sp,local,size))
            return 'http'
        except SystemExit:raise
        except Exception as ex:
            _pex=ex
            err('note: port failed (%s); trying envd fallback'%ex)
    _cp_envd_guard(o,size,_pex)
    try:
        _val(o,'reading %s:%s'%(sl,sp),lambda:_cp_envd_stream(sb,c,sp,local,size))
        return 'stream'
    except SystemExit:raise
    except Exception as ex:
        die(3,'cp failed: port and envd both unusable. Port needs python3; envd keeps RAM allocated.')
def _cp_cap_err(ex):
    m=str(ex).lower()
    return any(x in m for x in ('413','too large','not enough disk space','no space','enospc','quota','exceeds','disk space','1304'))
def _cp_cap_die(ex):
    die(3,'cp: upload failed - the file does not fit in the sandbox disk\n'
          'why   the server refused it (%s); a sandbox disk is fixed at create time\n'
          'fix   free space inside (csb rm <id>:/path), start from a template with a bigger disk, or split the file'%str(ex)[:160])
def _cp_put(sb,c,o,sl,tgt,local,size):
    try:return _cp_put_raw(sb,c,o,sl,tgt,local,size)
    except SystemExit:raise
    except Exception as ex:
        if _cp_cap_err(ex):_cp_cap_die(ex)
        raise
def _cp_put_raw(sb,c,o,sl,tgt,local,size):
    via=_cp_route(o,size)
    if via=='http':
        try:
            _val(o,'sending %s over the sandbox port'%os.path.basename(local),lambda:_cp_put_http(sb,c,sl,tgt,local,size))
            return 'http'
        except SystemExit:raise
        except Exception as ex:
            err('note: port failed (%s); trying envd fallback'%ex)
            _cp_envd_guard(o,size,ex,up=True)
    if size is not None and int(size)>16*1048576:
        _val(o,'sending %s in 16 MiB slices'%os.path.basename(local),lambda:_cp_slices(sb,c,sl,tgt,local,size))
        return 'slices'
    fs=_fs(sb,c)
    with open(local,'rb') as fh:blob=fh.read()
    fs.write_files([(tgt,blob)])
    return 'files'
def _is_skip(name,is_dir):
    if is_dir:return name in _SKIP_DIRS or name.startswith('.csb')
    return name.endswith(_SKIP_SUF)
def cmd_cp(o,c):
    args=o['_']
    if len(args)<2:die(2,'cp: <src> <id>:<path> (or reverse / multi-source to dir)')
    dry_only(o,'copy %s'%' '.join(args))
    allf=bool(o.get('all'))
    dest=args[-1];sources=args[:-1]
    if not any(':' in a for a in sources) and ':' in dest:
        dl,dp=_split_obj(o,dest);sb,_=_find_sb(dl,c)
        if not sb:die(2,_sbnope(dl,c))
        fs=_fs(sb,c);n=0;batch=[];has_dir=any(os.path.isdir(s) for s in sources)
        dest_file=not has_dir and not dp.endswith('/') and len(sources)==1
        for src in sources:
            if os.path.isdir(src):
                for root,ds,fsn in os.walk(src):
                    if not allf:
                        ds[:]=[d for d in ds if not _is_skip(d,True)]
                    for f in sorted(fsn):
                        if _is_skip(f,False) and not allf:continue
                        full=os.path.join(root,f);rel=os.path.relpath(full,src)
                        _sz=os.path.getsize(full)
                        _t=dp.rstrip('/')+'/'+rel.replace(os.sep,'/')
                        if _cp_route(o,_sz)!='files' or _sz>16*1048576:
                            try:_val(o,'creating the directories',lambda:fs.make_dir(_t.rsplit('/',1)[0]or'/'))
                            except Exception as _e:_swallow('cp',_e)
                            _cp_put(sb,c,o,dl,_t,full,_sz);n+=1;continue
                        with open(full,'rb') as fh:blob=fh.read()
                        batch.append((dp.rstrip('/')+'/'+rel.replace(os.sep,'/'),blob))
                continue
            if not os.path.isfile(src):die(3,'local source not a file: %s'%src)
            _sz=os.path.getsize(src)
            _tgt0=dp if dest_file else (dp.rstrip('/')+'/'+os.path.basename(src))
            if _cp_route(o,_sz)!='files' or _sz>16*1048576:
                try:_val(o,'creating the directories',lambda:fs.make_dir(_tgt0.rsplit('/',1)[0]or'/'))
                except Exception as _e:_swallow('cp',_e)
                _cp_put(sb,c,o,dl,_tgt0,src,_sz);n+=1;continue
            tgt=_tgt0
            with open(src,'rb') as fh:blob=fh.read()
            batch.append((tgt,blob))
        if batch:
            _hit=[]
            for _p,_b in batch:
                try:fs.stat(_p);_hit.append(_p)
                except Exception as _e:_swallow('cp',_e)
            if _hit and not o.get('yes') and not o.get('dry-run') and not is_tty():
                die(2,'target already exists; pass --yes to overwrite (non-tty)\nfix   csb cp <local> <id>:<path> --yes')
            if _hit and not confirm(o,'%s of %s already exist on %s:%s (e.g. %s) - overwrite?'%(_pl(len(_hit),'file','files'),_pl(len(batch),'file','files'),dl,dp,_hit[0]),why='overwriting files in the sandbox'):return 1
            need=[]
            for p,_ in batch:
                par='/'.join(p.split('/')[:-1])
                if par and par not in need:need.append(par)
            for par in sorted(need,key=len):
                try:_val(o,'creating the directories',lambda:fs.make_dir(par))
                except Exception as _e:_swallow('cp',_e)
            try:n+=_val(o,'uploading %d file(s) to %s:%s'%(len(batch),dl,dp),lambda:fs.write_files(batch))
            except Exception as ex:die(3,'upload failed: %s'%ex)
        if is_json(o):out_json({'copied':n,'to':'%s:%s'%(dl,dp)})
        else:print(_nump('copied %d file(s) -> %s:%s'%(n,dl,dp)))
        return 0
    if ':' in sources[0] and not any(':' in a for a in sources[1:]):
        sl,sp=_split_obj(o,sources[0]);sb,_=_find_sb(sl,c)
        if not sb:die(2,_sbnope(sl,c))
        fs=_fs(sb,c);local=dest
        def _isd(e):return bool(e.get('is_dir')or str(e.get('type')or'').endswith('DIRECTORY'))
        def _nm(e):return e.get('name')or(e.get('path','').split('/')[-1])
        def _pull(rp,ld):
            try:out=_val(o,'listing %s:%s'%(sl,rp),lambda:fs.list(rp))
            except Exception as ex:die(3,'cp: cannot list %s:%s (%s)'%(sl,rp,ex))
            n=0
            for ent in out:
                name=_nm(ent)
                if _is_skip(name,_isd(ent)) and not allf:continue
                full=rp.rstrip('/')+'/'+name
                if _isd(ent):
                    sub=os.path.join(ld,name);os.makedirs(sub,exist_ok=True);n+=_pull(full,sub);continue
                try:_fz=fs.stat(full).get('size')
                except Exception:_fz=None
                _cp_get(sb,c,o,sl,full,os.path.join(ld,name),_fz)
                n+=1
            return n
        want_dir=os.path.isdir(local) or local.endswith('/')
        if not want_dir:
            try:want_dir=_isd(_val(o,'reading %s:%s'%(sl,sp),lambda:fs.stat(sp)))
            except Exception:want_dir=False
        if want_dir:
            if os.path.exists(local)and not confirm(o,'%s already exists - write into it (files may be overwritten)?'%local,why='overwriting local files'):return 1
            if os.path.exists(local)and not os.path.isdir(local):
                die(2,'%s is a file; %s:%s is a directory\nfix   move %s aside first'%(local,sl,sp,local))
            os.makedirs(local,exist_ok=True)
            n=_pull(sp,local)
            if is_json(o):out_json({'copied':n,'from':'%s:%s'%(sl,sp),'to':local})
            else:print(_nump('copied %d file(s) <- %s:%s'%(n,sl,sp)))
            return 0
        _sz=None
        try:_sz=fs.stat(sp).get('size')
        except Exception as _e:_swallow('cp',_e)
        _sz=int(_sz)if _sz is not None else None
        if os.path.exists(local)and not confirm(o,'%s already exists - overwrite it?'%local,why='overwriting the local file'):return 1
        _how=_cp_get(sb,c,o,sl,sp,local,_sz)
        if is_json(o):out_json({'copied':1,'from':'%s:%s'%(sl,sp),'to':local,'via':_how})
        else:print(_nump('copied %s <- %s:%s  (%s, via %s)'%(_pl(1,'file','files'),sl,sp,_cp_size(_sz)if _sz else'?',_how)))
        return 0
    die(2,'cp: <local> <id>:<path> | <id>:<path> <local> | <local>... <id>:<dir>')
def cmd_fls(o,c):
    label,path=_split_obj(o,_obj_only(o,'ls-file','ls-file: <id>:<path>'))
    sb,_=_find_sb(label,c)
    if not sb:die(2,_sbnope(label,c))
    out=_fs(sb,c).list(path)
    if is_json(o):out_json(out);return 0
    if not out:print('(empty directory - nothing inside %s)'%path);return 0
    rows=[]
    for e in out:
        name=e.get('name') or (e.get('path','').split('/')[-1])
        typ='d' if e.get('is_dir') or str(e.get('type')or'').endswith('DIRECTORY') else '-'
        rows.append([name,typ,str(e.get('size')or'')])
    fmt(['NAME','T','SIZE'],rows);return 0
def cmd_mk(o,c):
    _raw=need_arg(o,'mk: <id>:<path>')
    label,path=_split_obj(o,_raw)
    if ':' not in _raw:die(2,'mk: %s needs a colon - add it:  csb mk %s:/newdir\n    a bare id means the ROOT directory "/"'%(_raw,_raw))
    sb,_=_find_sb(label,c)
    if not sb:die(2,_sbnope(label,c))
    if o.get('dry-run'):
        _ex=False
        try:_fs(sb,c).stat(path);_ex=True
        except Exception:_ex=False
        if _ex:
            if is_json(o):out_json({'dry_run':True,'action':'make the directory %s'%_raw})
            else:print('dry-run: %s already exists (would fail) - nothing was changed'%_raw)
            return 0
        dry_only(o,'make the directory %s'%_raw)
    _fs(sb,c).make_dir(path)
    if is_json(o):out_json({'path':'%s:%s'%(label,path)})
    else:print('made %s:%s'%(label,path))
    return 0
def cmd_mv(o,c):
    if len(o['_'])<2:die(2,'mv: <id>:<src> <id>:<dst>')
    if len(o['_'])>2:die(2,'mv: two objects only - each side is <id>:<path>\n  fix   csb mv <id>:/old <id>:/new')
    l1,p1=_split_obj(o,o['_'][0]);l2,p2=_split_obj(o,o['_'][1])
    if l1!=l2:die(2,'mv: both sides must be same sandbox (rename is in-sandbox)')
    sb,_=_find_sb(l1,c)
    if not sb:die(2,_sbnope(l1,c))
    try:_dst=bool(_fs(sb,c).stat(p2))
    except Exception:_dst=False
    dry_only(o,'move %s:%s -> %s:%s'%(l1,p1,l2,p2),why='moving %s:%s'%(l1,p1))
    if _dst and not confirm(o,'move %s:%s -> %s:%s? (that target already exists)'%(l1,p1,l2,p2),why='moving %s:%s'%(l1,p1)):return 1
    _fs(sb,c).rename(p1,p2)
    if is_json(o):out_json({'from':'%s:%s'%(l1,p1),'to':'%s:%s'%(l1,p2)})
    else:print('moved %s:%s -> %s'%(l1,p1,p2))
    return 0
def cmd_rmf(o,c):
    _raw=need_arg(o,'rm: <id>:<path>')
    label,path=_split_obj(o,_raw)
    if ':' not in _raw:die(2,'rm: %s needs a colon (a bare id means the ROOT directory "/")\n  fix   csb rm %s:/path --yes'%(_raw,_raw))
    sb,_=_find_sb(label,c)
    if not sb:die(2,_sbnope(label,c))
    if not confirm(o,'rm %s:%s? (irreversible)'%(label,path),why='removing %s:%s'%(label,path)):return 1
    _fsx=_fs(sb,c)
    try:_fsx.stat(path);_had=True
    except Exception:_had=False
    _fsx.remove(path)
    if is_json(o):out_json({'removed':'%s:%s'%(label,path)} if _had else {'removed':None,'note':'nothing to remove','path':'%s:%s'%(label,path)})
    else:print('removed %s:%s'%(label,path) if _had else 'nothing to remove %s:%s'%(label,path))
    return 0
def _wtp(t):
    s=str(t or'').strip()
    if s.upper().startswith('EVENT_TYPE_'):s=s[11:]
    return s.lower()or'event'
def cmd_watch(o,c):
    if is_json(o):die(2,'watch is streaming; no json mode (use default output)')
    if o.get('dry-run'):dry_only(o,'watch %s'%' '.join(o['_']),why='watching for filesystem events')
    label,path=_split_obj(o,_obj_only(o,'watch','watch: <id>:<path>'))
    sb,_=_find_sb(label,c)
    if not sb:die(2,_sbnope(label,c))
    w=_fs(sb,c).watch_dir(path)
    err('watching %s in %s - events print one per line, this directory only (not recursive)'%(path,sb.get('label')or label))
    try:
        for ev in w:
            if ev is None:continue
            name=getattr(ev,'name',None) or (ev.get('name')if isinstance(ev,dict)else None)
            print('%s %-7s %s'%(_disp(_rawnow().isoformat()),_wtp(getattr(ev,'type',None)or(ev.get('type')if isinstance(ev,dict)else None)),_cln(name or'')),flush=True)
    except KeyboardInterrupt:
        err('stopped watching %s'%path);return 0
def _snap_ledger_write(sid,e,c):
    led(c)[sid]=e;save_led(c)
SNAP_PG=100
SNAP_PGMAX=50
SNAP_CANDMAX=20
SNAP_UNREAD='the snapshot list could not be read'
def _snap_unread(e):return '%s (%s)'%(SNAP_UNREAD,e)
def _snap_hiccup(why):
    return bool(why)and str(why).startswith(SNAP_UNREAD)
_SNAPW=set()
def _snapwarn(why):
    if why in _SNAPW:return
    _SNAPW.add(why)
    err('warning: %s - entries KEPT; only a server 404 removes them.'%why)
def _snap_gone(c,sid):
    from urllib.parse import quote
    try:return _get_json(c,'/templates/'+quote(sid))is None
    except Exception:return False
def _snap_list(c):
    import requests
    from urllib.parse import quote
    items=[];tok=None
    for _ in range(SNAP_PGMAX):
        try:
            r=requests.get(c['api']+'/snapshots?limit=%d'%SNAP_PG+('&nextToken=%s'%quote(tok)if tok else''),headers=_auth_hdrs(c),timeout=_http_secs())
            if r.status_code==404:return None,False,'the snapshot list answered 404'
            r.raise_for_status();body=r.json()
        except Exception as e:return None,False,_snap_unread(e)
        page=[x for x in(body or[])if isinstance(x,dict)]
        items+=page
        nxt=(r.headers.get('x-next-token')or'').strip()or None
        if not nxt:
            if len(body or[])<SNAP_PG:return items,True,None
            return items,False,'the snapshot list came back as one full page (%d items) with no cursor'%SNAP_PG
        if nxt==tok:return items,False,'the snapshot list handed back the same cursor twice'
        tok=nxt
    return items,False,'the snapshot list was still paging after %d pages'%SNAP_PGMAX
def snap_facts(c):
    body,_ok,why=_snap_list(c)
    if body is None:return None,why,_ok
    out={}
    for x in body:
        if not isinstance(x,dict):continue
        sid=x.get('snapshotID')or x.get('snapshot_id')
        _n=x.get('names');_n=_n if isinstance(_n,list)else[]
        if sid:out[sid]={'status':x.get('status')or'','backend':x.get('backend')or'',
                         'names':[v for v in _n if v],'created':x.get('createdAt')or'',
                         'origin':x.get('originSandboxID')or''}
    return out,None,_ok
def _fetch_snaps(c,sandbox_id=None):
    try:
        out=[];tok=None
        for _ in range(SNAP_PGMAX):
            items,tok=_Sandbox().list_snapshots(sandbox_id=sandbox_id,limit=SNAP_PG,next_token=tok,config=sdk(c))
            out+=list(items or[])
            if not tok:break
        return out
    except Exception as ex:die(3,'list_snapshots failed: %s'%ex)
def fetch_snap_origins(c=None,prune=True):
    c=c or cfg()
    try:
        body,full,why=_snap_list(c)
        if body is None:return{}
        out={};ids=set()
        for x in(body or[]):
            if not isinstance(x,dict):continue
            sid=x.get('snapshotID')or x.get('snapshot_id')
            org=x.get('originSandboxID')or x.get('origin')
            if not sid:continue
            ids.add(sid)
            if org:out[sid]=org
        if prune:
            cand=[k for k in led(c) if k not in ids]
            if cand and not full:_snapwarn(why)
            if len(cand)>SNAP_CANDMAX:_snapwarn('the snapshot list is missing %d local entries at once - the LIST is short, not the snapshots'%len(cand))
            else:
                L=led(c);gone=[k for k in cand if _snap_gone(c,k)]
                if gone:
                    for g in gone:L.pop(g,None);_LED_DEL.add(g)
                    save_led(c)
        return out
    except Exception:return{}

def snap_dups(c,name,tpls=None,snaps=None):
    out=[];seen=set()
    for sid,e in (led(c)or{}).items():
        if (e or{}).get('name')==name:out.append((sid,'ledger',(e or{}).get('origin')or''));seen.add(sid)
    if snaps is None:
        try:snaps=_snap_list(c)[0]
        except Exception:snaps=None
    for x in (snaps or[]):
        if not isinstance(x,dict):continue
        sid=x.get('snapshotID')or x.get('snapshot_id')or''
        if not sid or sid in seen:continue
        if name in(x.get('names')or[]):out.append((sid,'server',x.get('originSandboxID')or x.get('origin')or''));seen.add(sid)
    for t in (tpls if tpls is not None else _tpl_rows2(c))or[]:
        tid=t.get('id')or''
        if tid and tid not in seen and(t.get('alias')or'')==name:out.append((tid,'alias',''));seen.add(tid)
    return out
def snap_dup_msg(name,dups,label,c=None):
    _w={'ledger':'local ledger','server':'server list','alias':'template alias'}
    _k={'ledger':'snapshot','server':'snapshot','alias':'template'}
    out=['the name "%s" is already used (%d place(s))'%(name,len(dups))]
    for sid,src,org in dups[:4]:
        _lab=((reg(c)or{}).get('entries',{})or{}).get(org,{}).get('label')or'' if org else''
        _org=('from %s (%s)'%(_lab,short_id(org))if _lab else('from %s'%short_id(org)if org else''))
        out.append(('  %-14s %-9s %-13s %s'%(short_id(sid),_k.get(src,'?'),_w.get(src,src),_org)).rstrip())
    if len(dups)>4:out.append('  ... and %d more'%(len(dups)-4))
    out.append('  pick another name: csb snap %s <newname>'%(label))
    out.append('   or delete the old snapshot: csb snaps')
    return '\n'.join(out)
def snap_unlist_msg(label,name,why):
    return '\n'.join([
        'cannot check the name "%s": %s'%(name,why),
        '  the name must be free before the build starts - csb could not prove that',
        '  let csb pick the name:  csb snap %s'%label])
def snap_fail_msg(sb,label,name,ex,tpls=None):
    _id=sb.get('id')or'';_lb=(sb.get('label')or'').strip()or str(_id or label)[:8]
    _a=next((t['alias']for t in(tpls or[])if t.get('id')==sb.get('tpl')and t.get('alias')),None)
    return '\n'.join([
        'snapshot of %s failed: %s'%(_lb,_why_server(ex)),
        '  leftover:  csb snaps     clear:  csb snaprm <snapshot_id> --yes',
        '  next:  csb info %s then csb snap %s %s   |  still failing: csb kill %s --yes, csb start %s %s'%(
            _id,_id,name,_id,_a or'<template>',label)])
def cmd_snap(o,c):
    label=need_arg(o,'snap: <id> [name]   or: snap ls')
    if label=='ls':
        return cmd_snaps({'_': [], 'o': o.get('o')}, c)
    if o.get('list'):
        print('would snap %s%s'%(label,(' '+o['_'][1])if len(o['_'])>1 else''))
        print('snap - nothing was changed (--list)')
        return 0
    sb,_=_find_sb(label,c)
    if not sb:die(2,_sbnope(label,c))
    _need_run(sb,'csb snap')
    if sb.get('state')!='running':
        die(3,'snap needs runtime (state=%s)\nfix   csb resume %s --yes'%((sb.get('state')or'unknown'),sb.get('id')))
    fam=sb.get('family') or reg(c)['entries'].get(sb['id'],{}).get('family')
    existing=set(e.get('name')for e in led(c).values()if e.get('name'))
    _si,_sok,_swhy=_snap_list(c)
    _sbad=(_swhy or SNAP_UNREAD)if(_si is None or not _sok)else None
    if _sbad and len(o['_'])>1:
        die(2,snap_unlist_msg(label,o['_'][1],_sbad))
    if _sbad and not is_json(o):err('note: %s - a name clash cannot be checked this time'%_sbad)
    for x in (_si or[]):
        if isinstance(x,dict):existing.update(n for n in(x.get('names')or[])if n)
    _tl=_tpl_rows2(c)
    for t in _tl:
        if t['alias']:existing.add(t['alias'])
    _lb=(sb.get('label')or'').strip()or str(sb.get('id') or label)[:8]
    if len(o['_'])>1:
        name=o['_'][1]
        _dp=snap_dups(c,name,_tl,_si or[])
        if _dp:die(2,snap_dup_msg(name,_dp,label,c),kind='name_taken')
    else:
        date=datetime.datetime.now().strftime('%Y%m%d');name=snap_name(_lb,date,existing)
    _tg='%s (%s)'%(_lb,short_id(sb.get('id')or''))if sb.get('label')else _lb
    lim=_lim(_stop_secs())
    dry_only(o,'snap %s as %s'%(_tg,name),why='taking a snapshot of %s'%label)
    _res,_j=_watch(o,'snapshotting %s ...'%_tg,lambda:_inst(sb,c).create_snapshot(name=name),lim)
    _ex=_re(_j)
    if _res!='ok':
        die(1 if _res=='stop'else 3,'snap %s: %s\n%s'%(label,
            'stopped watching'if _res=='stop'else'no answer for %ds (raise it: CSB_STOP_WAIT)'%int(lim),_snap_still(label)))
    if _ex is not None:die(3,snap_fail_msg(sb,label,name,_ex,_tl),raw=str(_ex))
    si=_j['box'].get('val')
    sid=si.snapshot_id if not isinstance(si,str) else si
    ts0=_srv_tpl_ts(c,sid)
    _snap_ledger_write(sid,{'label':_lb,'name':name,'fam':fam,'origin':sb['id'],'ts':ts0 or _now()},c)
    if is_json(o):out_json({'snapshot_id':sid,'name':name})
    else:
        _okl('taken',sid,name)
    return 0
def _snap_still(label):
    return('  the request is already with the server, which keeps building the snapshot:\n'
           '    csb snaps %s      (it appears there when it lands - do not run snap again)'%label)
_THEMES=('D02','D04o','D14','D03','D01')
_UIALIAS={'plain':'D02','green':'D03','neon':'D04o'}
_THEMEERR=[None]
def _apply_ui():
    global _ASC,_ELT,HELP_TAIL,TUI_HELP_ROWS
    _ASC=_box_ascii();_ELT=('...'if _ASC else chr(0x2026))
    HELP_TAIL=('Keep your agents sandboxed.'if _ASC else'(๑˃ᴗ˂)و  Keep your agents sandboxed.')
    TUI_HELP_ROWS=tuple((a,b,('+/-5 nodes (crosses parents)'if _ASC else'±5 nodes (crosses parents)')if c in('+/-5 nodes (crosses parents)','±5 nodes (crosses parents)')else c)for a,b,c in TUI_HELP_ROWS)
    return _ASC
def _theme_get(c=None):
    v=prefs_read(c).get('theme')
    return v if isinstance(v,str) and v else None
def _theme_step(c,cur=None):
    if cur is None:cur=_theme_get(c)or'D02'
    cur=_UIALIAS.get(cur,cur)
    if cur not in _THEMES:cur='D02'
    nx=_THEMES[(_THEMES.index(cur)+1)%len(_THEMES)]
    try:_pref_put(c,theme=nx);_THEMEERR[0]=None
    except Exception as e:_THEMEERR[0]=type(e).__name__
    return nx
def _spin(msg):
    if _sw('auto_no_spin'):return lambda:None
    if not sys.stderr.isatty():
        sys.stderr.write(msg+'\n');sys.stderr.flush()
        return lambda:None
    import threading,time
    st=[True,0]
    def loop():
        while st[0]:
            time.sleep(1)
            if st[0]:sys.stderr.write('\r   %s waited %ds   '%(msg,st[1]));st[1]+=1;sys.stderr.flush()
    threading.Thread(target=loop,daemon=True).start()
    def stop():
        st[0]=False;sys.stderr.write('\r'+' '*72+'\r');sys.stderr.flush()
    return stop
def _pick(items,o,what):
    if not items:die(3,'no %s found'%what)
    if len(items)==1:return items[0]
    if not is_tty():die(2,'ambiguous %s: pass exact id (--yes) or run interactively'%what)
    for i,it in enumerate(items,1):
        print('%2d) %s'%(i,it))
    try:r=input('select 1-%d> '%len(items))
    except EOFError:die(1,'cancelled')
    if not r.isdigit()or not 1<=int(r)<=len(items):die(1,'cancelled')
    return items[int(r)-1]
def _idhint(c,arg):
    a=str(arg or'').strip();E=(reg(c)or{}).get('entries')or{}
    if not re.fullmatch('[0-9a-f]{4,23}',a):return''
    h=[i for i in E if str(i).startswith(a)]
    if len(h)!=1:return''
    return'%s is a display form - in full:  %s\n  commands take the full id (the full id: csb ls -o json prints it)'%(a,h[0])
def _infonope(x,c):
    if str(x).startswith('snap-'):
        return'unknown sandbox: %s (that is a snapshot - csb snaps lists them; csb ls lists sandboxes)'%x
    try:
        if any(t.get('id')==x or(t.get('alias')or'')==x for t in tpl_rows(c)):
            return'unknown sandbox: %s (that is a template - csb tpl ls lists them; csb ls lists sandboxes)'%x
    except Exception:pass
    return _sbnope(x,c)
def _sbnope(x,c=None):
    return 'no sandbox: %s\nfix   csb ls lists them; full ids: csb ls -o json%s'%(x,_idhint(c,x)if c is not None else'')
def _rb_hint(x,c):
    try:
        org=fetch_snap_origins(c);nm={}
        for t in tpl_rows(c):
            if t.get('is_snap')and t.get('alias'):nm[str(t['alias'])]=t['id']
        for s0,e0 in led(c).items():
            if e0.get('name'):nm.setdefault(str(e0['name']),s0)
        sid=nm.get(x)or next((k for k in org if k==x or k.startswith(x)),None)
        if not sid:return''
        o=org.get(sid)
        if not o:return'\n  %r is a snapshot on the server - roll back its sandbox instead:\nfix   csb rb <id> %s'%(x,sid)
        lab=next((s.get('label')for s in fetch_sbs(c)if s.get('id')==o),None)or o[:8]
        return'\n  %r is a snapshot, not a sandbox - name the sandbox to roll back:\nfix   csb rb %s %s'%(x,lab,sid)
    except Exception:return''

def _rb_elsewhere(c,label,want):
    if not want:return None
    body,_,_=_snap_list(c)
    for x in(body or[]):
        sid=x.get('snapshotID')or''
        _nms=[n for n in(x.get('names')or[])if n]
        _l=(led(c).get(sid)or{}).get('name')
        if _l:_nms.append(_l)
        if sid!=want and want not in _nms:continue
        org=x.get('originSandboxID')or''
        who=(reg(c)['entries'].get(org)or{}).get('label')or(short_id(org)if org else'')
        nm=(_nms or[sid])[0]
        return ('%s is a snapshot of %s, not of %s\n'
                '  rollback restores a sandbox from its own snapshot\n'
                '  instead   start a new sandbox from it:  csb start %s'%(sid,who or'another sandbox',label,nm))
    return None
def _snap_cands(c,arg):
    _out=[]
    for _s in _fetch_snaps(c):
        _sid=_s.snapshot_id if hasattr(_s,'snapshot_id') else _s.get('snapshotID')
        _nm=getattr(_s,'names',None)or((_s.get('names')if isinstance(_s,dict) else None)or[])
        if _sid and(_sid==arg or arg in _nm or arg==(led(c).get(_sid)or{}).get('name')):_out.append(_sid)
    return _out
def cmd_rb(o,c):
    _a=o.get('_')or[]
    if len(_a)==1 and not str(_a[0]).startswith('snap-') and not _find_sb(str(_a[0]),c)[0]:
        _cd=_snap_cands(c,str(_a[0]))
        if len(_cd)>1:
            die(2,'rb: "%s" matches %s - pick one:\n  %s'%(_a[0],_pl(len(_cd),'snapshot','snapshots'),'\n  '.join(x[:12] for x in _cd)))
        if _cd:_a=[_cd[0]]
    if len(_a)==1 and str(_a[0]).startswith('snap-'):
        _body,_,_=_snap_list(c)
        _row=next((x for x in(_body or[])if isinstance(x,dict)and(x.get('snapshotID')or x.get('snapshot_id'))==_a[0]),None)
        if _row is not None:
            _org=_row.get('originSandboxID')or _row.get('origin')or''
            if not _org:die(2,'snapshot %s has no source sandbox on the server - nothing to roll back'%_a[0])
            _own,_=_find_sb(_org,c)
            if not _own:die(2,'snapshot %s belongs to a sandbox the server no longer lists: %s'%(_a[0],short_id(_org)))
            _lab=(reg(c)['entries'].get(_own['id'])or{}).get('label')or _own.get('label')or short_id(_own['id'])
            err('note: %s is a snapshot of %s - rolling that one back'%(_a[0],_lab))
            o=dict(o);o['_']=[_own['id'],_a[0]]
    label=need_arg(o,'rb: <sandbox> <snapshot id>   (or just the snapshot id|name)');sb,_=_find_sb(label,c)
    if not sb:
        _hint=_rb_hint(label,c)
        if not _hint:die(2,_sbnope(label,c))
        die(2,'unknown sandbox: %s%s'%(label,_hint))
    want=o['_'][1] if len(o['_'])>1 else None
    if sb.get('state')!='running':
        die(3,'rb needs a running sandbox (state=%s) - resume first:  csb resume %s --yes'%(sb.get('state'),sb.get('id')))
    snaps=[s for s in _fetch_snaps(c,sandbox_id=sb['id'])]
    if not snaps:
        _el=_rb_elsewhere(c,label,want)
        if _el:die(2,_el)
        die(3,'no snapshots for %s\nfix   csb snap %s <name>'%(label,label))
    shown=[]
    for s in snaps:
        sid=s.snapshot_id if hasattr(s,'snapshot_id') else s.get('snapshotID')
        names=getattr(s,'names',None) or (s.get('names')if isinstance(s,dict)else[])
        shown.append('%s %s'%(sid,','.join(_real_names(names,sid))))
    if want:
        ids=[x.split(' ')[0] for x in shown]
        if want not in ids:
            _pre=[i for i in ids if i.startswith(want)]
            if _pre:
                die(2,'rb takes the full snapshot id, not a prefix:\n  %s  ->  %s'%(want,_pre[0]))
            _nm=[]
            for i in ids:
                _row=[r for r in shown if r.split(' ',1)[0]==i][0]
                _nms=[n for n in (_row.split(' ',1)[1].split(',')if ' ' in _row else[])if n]
                _nms.append((led(c).get(i)or{}).get('name'))
                if want in _nms:_nm.append(i)
            if _nm:
                die(2,'rb takes the full snapshot id, not a name:\n  %s  ->  %s'%(want,_nm[0]))
            die(2,'no snapshot %r for %s - available: %s'%(want,label,', '.join(shown)))
        sid=want
    else:sid=None
    if not confirm(o,'rollback %s to a snapshot? (irreversible for current state; snapshot kept)'%label,why='rolling %s back'%label):return 1
    if sid is None:sid=_pick(shown,o,'snapshots').split(' ')[0]
    lim=_lim(_stop_secs())
    _res,_j=_watch(o,'rolling back %s ...'%label,lambda:_inst(sb,c).rollback(sid),lim)
    _e=_re(_j)
    if _res!='ok':
        die(1 if _res=='stop'else 3,'rb %s: already sent (a second one rolls back)\nfix   csb info %s'%(
            label,sb.get('id')))
    if _e is not None:
        m=str(_e)
        if '130400' in m or 'restore sandbox runtime' in m:
            err('rb failed: %s'%m)
            err('  stuck sandbox - csb admin -- cubemastercli %s cubebox destroy %s'%(cm_txt(),sb['id']))
            err('  then its snapshots can be deleted again')
        raise _e
    if is_json(o):out_json({'sandbox_id':sb['id'],'snapshot_id':sid})
    else:
        _okl('rolled back to %s'%((led(c).get(sid)or{}).get('name')or short_id(sid)),sb['id'],label)
    return 0
def cmd_snaps(o,c):
    label=o['_'][0] if o.get('_') else None
    if label:
        sb,_=_find_sb(label,c)
        if not sb:die(2,_sbnope(label,c))
        snaps=_fetch_snaps(c,sandbox_id=sb['id'])
    else:snaps=_fetch_snaps(c)
    facts,why,_ok=snap_facts(c)
    if facts is not None and not _ok:
        err('warning: this list may be incomplete - nothing was removed.')
    if facts is None:
        err('warning: %s - STATUS/BACKEND blank (server record not read). nothing was removed.'%why)
    rows=[];_raw={}
    for s in snaps:
        sid=s.snapshot_id if hasattr(s,'snapshot_id') else s.get('snapshotID')
        names=getattr(s,'names',None) or (s.get('names')if isinstance(s,dict)else[])
        e=led(c).get(sid)or{}
        _raw[sid]=[x for x in(names or[])if x]
        nm=_real_names(names,sid)
        if e.get('name')and e['name']not in nm:nm.append(e['name'])
        f=(facts or {}).get(sid)or{}
        rows.append([sid,','.join(nm),e.get('fam')or'',f.get('status')or'',f.get('backend')or'',e.get('ts')or''])
    rows.sort(key=lambda r:_tkey(r[5]),reverse=True)
    if is_json(o):
        out_json([{'snapshot_id':r[0],'names':_raw.get(r[0],[]),'family':r[2],'ts':r[5],
                   'status':r[3]or None,'backend':r[4]or None}for r in rows]);return 0
    if not rows:print('(no snapshots - make one:  csb snap <sandbox>)')
    else:fmt(['SNAPSHOT ID','NAMES','FAMILY','STATUS','BACKEND','TS'],[[r[0],r[1],r[2],r[3],r[4],_disp(r[5])]for r in rows])
    return 0
def _snap_holders(sid,c):
    _exe=_env('CSB_CUBEMASTERCLI')or'cubemastercli'
    try:
        _p=subprocess.run([_exe]+cm_addr()+['snapshot','info','--snapshot-id',sid],
                          capture_output=True,text=True,timeout=25)
    except Exception:return None
    if _p.returncode!=0:return None
    t=(_p.stdout or'')+(_p.stderr or'')
    m=re.search(r'runtime_ref_count:\s*(\d+)',t)
    if not m:return None
    ids=[]
    for line in t.splitlines():
        if 'runtime_ref_sandboxes' in line:
            ids+=[x for x in re.split(r'[,\s]+',line.rsplit('runtime_ref_sandboxes:',1)[-1].strip())if re.fullmatch(r'[0-9a-f]{32}',x)]
    return int(m.group(1)),ids

def cmd_snaprm(o,c,who='snaprm'):
    if len(o['_'])<1:die(2,'%s: <snapshot_id|name> [--yes]'%who)
    arg=o['_'][0]
    if o.get('dry-run'):
        if is_json(o):out_json({'dry_run':True,'action':'delete snapshot %s'%arg})
        else:print('dry-run: delete snapshot %s - nothing was changed'%arg)
        sys.exit(0)
    if not is_tty() and not o.get('yes'):
        if not confirm(o,'delete snapshot %s? (irreversible)'%arg,why='deleting snapshot %s'%arg):return 1
    snaps=_val(o,'reading the snapshots',lambda:_fetch_snaps(c))
    cand=[];snm={}
    for s in snaps:
        sid=s.snapshot_id if hasattr(s,'snapshot_id') else s.get('snapshotID')
        names=getattr(s,'names',None) or (s.get('names')if isinstance(s,dict)else[])
        if sid:snm[sid]=[x for x in(names or[])if x]
        if sid==arg or arg in names or arg==(led(c).get(sid)or{}).get('name'):cand.append(sid)
    if not cand:
        if arg in led(c):cand=[arg]
        else:
            av=[]
            for s0 in snaps:
                _i=s0.snapshot_id if hasattr(s0,'snapshot_id')else s0.get('snapshotID')
                _n=_real_names((getattr(s0,'names',None)or(s0.get('names')if isinstance(s0,dict)else None)or[]),_i)[:1]
                av.append('%s%s'%(_i[:12],('(%s)'%_n[0])if _n else''))
            die(2,'unknown snapshot: %s%s'%(arg,('  csb snaps lists: '+', '.join(av[:6]))if av else'  (the server has no snapshots right now)'))
    if len(cand)>1 and arg not in cand:
        _ids=sorted(cand)
        die(2,'%s takes the full snapshot id, not a name:  %s -> %s%s'%(
            who,arg,_ids[0],('' if len(_ids)==1 else '  (+%d more, see csb snaps)'%(len(_ids)-1))))
    if not is_json(o):
        for _sid in sorted(set(cand)):
            _an=[x for x in(snm.get(_sid)or[])if x and x!=_sid]
            if arg!=_sid or _an:print('  snapshot  %s%s'%(_sid,('  '+', '.join(_an))if _an else''))
    if not confirm(o,'delete snapshot %s? (irreversible)'%(','.join(short_id(x) for x in sorted(set(cand)))),why='deleting snapshot %s'%arg):return 1
    _lv=_val(o,'reading the sandboxes',lambda:fetch_sbs(c))
    _og=_snap_orgs(c)
    _hold={}
    _force=bool(o.get('force'))
    _confirmed=False
    for sid in set(cand):
        _ho=[(x.get('label')or x['id'][:8],x['id'],x.get('state')or'?')for x in _lv if x.get('tpl')==sid]
        _ph=_snap_holders(sid,c)
        _hold[sid]=(_ho,_ph)
        _pr=_ph[0]if _ph else 0;_pids=[x for x in(_ph[1]if _ph and len(_ph)>1 else[])if x]
        if _pr:
            _lbl={s['id']:(s.get('label')or short_id(s['id']))for s in _lv}
            _who=', '.join('%s (%s)'%(_lbl.get(i)or'(not in this ledger)',short_id(i))for i in _pids)or\
                 ('the platform did not name them - ask it:  csb admin -- cubemastercli snapshot info --snapshot-id %s'%sid)
            _m='snaprm refused: %s has %d live ref(s): %s'%(short_id(sid),_pr,_who)
            _m+='\n  fix   csb snaprm %s --yes --force   (those sandboxes keep running)'%sid
            if not _force and not confirm(o,_m,why='deleting a snapshot with %d live ref(s)'%_pr):return 1
            _confirmed=not _force
            _force=True
            if not is_json(o):
                sys.stderr.write('note: %s still has %d live ref(s) (%s) - deleting it anyway; they keep running, the link goes\n'%(short_id(sid),_pr,_who))
        if _ho and not _force:
            _who=', '.join('%s (%s)'%(x[0],short_id(x[1]))for x in _ho)
            _m='snaprm refused: %s is referenced by %s'%(short_id(sid),_who)
            _m+='\n  fix   csb snaprm %s --force   (they keep running; the link goes)'%sid
            die(2,_m)
        if not is_json(o)and _ho:
            sys.stderr.write('note: %s is still named by %s - deleting it anyway%s; they keep running, the link goes\n'%(sid,', '.join([x[0]for x in _ho]),' (live refs confirmed)'if _confirmed else' (--force given)'))
        import time as _t
        err=None
        for i in range(8):
            try:
                _val(o,'deleting the snapshot %s'%sid,lambda:_Sandbox().delete_snapshot(sid,config=sdk(c)));err=None;break
            except Exception as ex:
                err=ex
                if '130409' not in str(ex):break
                if not is_json(o):sys.stderr.write('\r   waiting refcount drain (%d/8)...'%(i+1));sys.stderr.flush()
                if i<7:_t.sleep(3)
        if not is_json(o):sys.stderr.write('\n')
        if err is not None:
            if '404' in str(err):led(c).pop(sid,None);_LED_DEL.add(sid)
            else:
                _ph=_snap_holders(sid,c)if'130409'in str(err)else None
                _ho,_ph0=_hold.get(sid,([],None))
                _extra='\n  the platform says %d active runtime ref(s)%s'%( _ph[0],(': '+', '.join(x[:8]for x in _ph[1][:4]))if _ph and _ph[1] else'')if _ph else''
                if _ho:_extra+='\n  sandboxes still running from it:\n'+'\n'.join('    %-24s %-9s %s'%(x[0][:24],x[2],x[1])for x in _ho[:3])
                die(3,'delete_snapshot %s failed: still referenced (130409)%s\nfix   csb kill <id> --yes'
                    %(sid,_extra))
        led(c).pop(sid,None);_LED_DEL.add(sid)
    save_led(c)
    _seen_gc(c,set(cand),_og)
    if is_json(o):out_json({'deleted':sorted(set(cand))})
    else:print('deleted %s'%(','.join(sorted(set(cand)))))
    return 0
DATE_TPL=re.compile(r'-\d{4}-\d{2}-\d{2}$')
def _sids_for(c,sid,orig=None):
    orig=orig if orig is not None else fetch_snap_origins(c,prune=False)
    L=led(c)
    return sorted({k for k,v in orig.items()if v==sid}|{k for k,e in(L or{}).items()if(e or{}).get('origin')==sid})
def _snap_argv(sids):
    return ['csb snaprm %s --yes'%x for x in list(sids)]
def _clip(s,w):
    if _dw(s)<=w:return s
    out=''
    for ch in s:
        if _dw(out+ch)>w-3:break
        out+=ch
    return out+'...'
def local_junk(reg_path) -> list:
    import glob as _g
    d=os.path.dirname(reg_path)or'. ';out=[];seen=set()
    _dirs=[d]
    if os.path.basename(os.path.abspath(d))=='ledger':
        _up=os.path.dirname(os.path.abspath(d))
        _dirs+=[os.path.join(_up,'config'),os.path.join(_up,'log')]
    for _d in _dirs:
        for pat in('*.bak-*','*.lock','audit.log.1','*.tmp.*'):
            for f in sorted(_g.glob(os.path.join(_d,pat))):
                try:
                    if os.path.basename(f).startswith('audit.log'):continue
                    if f in seen:continue
                    sz=os.path.getsize(f)
                    if pat=='*.lock' and sz:continue
                    seen.add(f);out.append((f,sz))
                except Exception:pass
    return sorted(out)
def _backup_file(q,ts):
    b='%s.bak-%s'%(q,ts)
    open(b,'wb').write(open(q,'rb').read())
    return b
def cmd_prune(o,c):
    if o.get('force'):
        die(2,'--force does not apply to prune (it only crosses dependencies; prune has none)\nfix   use --yes for confirmation, or --dry-run to inspect')
    live=_live_ids_full(c)
    if live is None:
        die(2,'prune: the cluster list is not COMPLETE - nothing was touched\n'
              'fix   retry when  csb ls  returns the full list (paging must finish)')
    _ent=reg(c)['entries']
    _d=dict(prefs(c).get('sbx')or{})
    do_e=bool(o.get('entries'))or not(bool(o.get('policies')))
    do_p=bool(o.get('policies'))or not(bool(o.get('entries')))
    dead_e=sorted([k for k in _ent if k not in live])if do_e else []
    dead_p=sorted([k for k in _d if k not in live and(k not in _ent or k in dead_e)])if do_p else []
    if not dead_e and not dead_p:
        if is_json(o):out_json({'dropped':0,'dead_entries':[],'dead_policies':[],'live_seen':len(live)})
        else:print('prune: nothing dead - all %d entries and %d policies are live or unknown-but-kept'%(len(_ent),len(_d)))
        return 0
    if o.get('dry-run'):
        if is_json(o):out_json({'dry_run':True,'dead_entries':dead_e,'dead_policies':dead_p,'live_seen':len(live)})
        else:
            print('dry-run: prune would drop %d dead ledger entr%s and %d dead sbx polic%s - nothing was changed'%(
                len(dead_e),'y'if len(dead_e)==1 else'ies',len(dead_p),'y'if len(dead_p)==1 else'ies'))
            for k in dead_e:print('  entry   %s  %s'%(k[:12],(_ent.get(k)or{}).get('label')or''))
            for k in dead_p:print('  policy  %s'%k[:12])
        return 0
    if not confirm(o,'prune dead records? %d entr%s, %d polic%s (a backup is written first)'%(
            len(dead_e),'y'if len(dead_e)==1 else'ies',len(dead_p),'y'if len(dead_p)==1 else'ies'),why='pruning dead records'):
        return 1
    import time as _t
    ts=_t.strftime('%Y%m%d-%H%M%S');baks=[]
    for q in (c['reg'],prefs_path(c)):
        if not os.path.exists(q):continue
        try:b=_backup_file(q,ts);baks.append(b)
        except Exception as ex:die(3,'could not back up %s (%s) - nothing was changed'%(q,ex))
    for k in dead_e:del _ent[k];_REG_DEL.add(k)
    if dead_e:save_reg(c)
    if dead_p:
        _d=dict(prefs(c).get('sbx')or{})
        for k in dead_p:_d.pop(k,None)
        save_prefs(c,sbx=_d)
    if is_json(o):out_json({'dropped':len(dead_e)+len(dead_p),'dead_entries':dead_e,'dead_policies':dead_p,'backups':baks,'live_seen':len(live)})
    else:
        print('prune: dropped %d dead ledger entr%s and %d dead sbx polic%s'%(len(dead_e),'y'if len(dead_e)==1 else'ies',len(dead_p),'y'if len(dead_p)==1 else'ies'))
        for b in baks:print('  backup: %s'%b)
    return 0
def _wipe_ledger(o,c):
    if o.get('force'):
        die(2,'--force does not apply to clean --ledger (it has no dependency to cross)\nfix   use --yes for confirmation')
    p=c['reg'];r=reg(c);hard=bool(o.get('hard'))
    ledp=c.get('led')or cfg()['led']
    hw=[q for q in _hw_targets(p)if os.path.exists(q)]
    if not r['entries']and not hard:
        try:open(p+'.empty','w',encoding='utf-8').write('emptied by csb clean --ledger\n')
        except Exception:pass
        err('the local ledger is already empty - kept as a deliberate clear')
        return 0
    n=len(r['entries'])
    if not confirm(o,'wipe all %d record(s) in %s?'%(n,p),why='wiping the ledger'):return 1
    if not confirm(o,'really wipe it? every name<->id binding goes away (a backup is written first)',why='wiping the ledger (second confirmation)'):return 1
    import time as _t
    ts=_t.strftime('%Y%m%d-%H%M%S');baks=[]
    def _bak(q):
        try:b=_backup_file(q,ts)
        except Exception as ex:die(3,'could not back up %s (%s) - nothing was changed'%(q,ex))
        baks.append(b);return b
    bak=_bak(p)
    if os.path.exists(ledp):_bak(ledp)
    for q in hw:_bak(q)
    r['entries']={};r['noauto']=[]
    if hard:
        r['templates']={};r['family_highwater']={}
    _fresh=json.loads(json.dumps(r));_fresh['entries']={};_fresh['noauto']=[]
    reg_write(p,_fresh);_bust()
    if hard:
        try:_atomic_write(ledp,{})
        except Exception as ex:die(3,'could not clear %s (%s)'%(ledp,ex))
        _hw_save(p,{})
    try:open(p+'.empty','w',encoding='utf-8').write('emptied by csb clean --ledger\n')
    except Exception:pass
    kept=[]if hard else['family_highwater','templates']
    if is_json(o):out_json({'wiped':n,'hard':hard,'backups':baks,'kept':kept})
    else:
        err('wiped %d record(s)%s'%(n,' (hard: snapshots, highwater and templates cleared)'if hard else'; family_highwater and templates were kept'))
        for b in baks:print('  backup: %s'%b)
        if hard:print('  undo:   cp <backup> <original> for each line above')
        else:print('  undo:   cp %s %s'%(bak,p))
        print('  every sandbox is [U] again - the next start adopts them once more')
    return 0
def cmd_clean(o,c):
    if o.get('ledger'):return _wipe_ledger(o,c)
    if o.get('hard'):die(2,'clean --hard only applies with --ledger')
    arg=need_arg(o,'clean: <id|snapshot-id|snapshot-name>')
    sbs,orig=_val(o,'reading the cluster',lambda:(fetch_sbs(c),fetch_snap_origins(c,prune=False)))
    E=reg(c)['entries']
    def _pfx(xs):
        c0=[x for x in xs if x==arg or(len(arg)>=24 and str(x).startswith(arg))]
        return c0[0]if len(c0)==1 else None
    live=[s for s in sbs if s['id']==arg or s.get('label')==arg]
    if not live:
        sid0=_pfx([s['id']for s in sbs])
        if sid0:live=[s for s in sbs if s['id']==sid0]
    if live:
        s=live[0];lab=s.get('label')or s['id'][:8];mines=_sids_for(c,s['id'],orig)
        m=['clean refused: %s is a LIVE sandbox (state=%s).'%(lab,s.get('state')or'?'),
           '  clean only clears [D]/[E] nodes and orphan snapshots.',
           '  --yes will not help: clean never removes a live sandbox.',
           '  csb kill %s%s'%(s['id'],' --yes'if not is_tty()else'')]
        if mines:
            m+=['  kill never deletes snapshots - delete them first:']+['    '+x for x in _snap_argv(mines)]+['  then  csb clean %s'%s['id']]
        else:
            m+=['  it owns no snapshot - kill alone removes the node.']
        die(3,'\n'.join(m))
    gid=next((i for i,e in E.items()if i==arg or(e or{}).get('label')==arg),None)or _pfx(list(E))
    if gid:
        e=E[gid];mines=_sids_for(c,gid,orig)
        kids=[i for i,x in E.items()if(x or{}).get('kind')=='clone'and(x or{}).get('parent')in(gid,e.get('label')or'')]
        if mines or kids:
            _lb=e.get('label')or gid[:8]
            if mines:
                m=['clean refused: %s is a [D] node (the sandbox was killed)'%_lb]
            else:
                m=['clean refused: %s is an [X] node - its sandbox was killed.'%_lb]
            if mines:
                _al={t['id']:t.get('alias')for t in _val(o,'reading the templates',lambda:tpl_rows(c))};_L=led(c)
                _nm=[((_L.get(x)or{}).get('name')or _al.get(x)or short_id(x))for x in mines]
                _s=', '.join(_nm[:8])+('  ... +%d more'%(len(_nm)-8)if len(_nm)>8 else'')
                m+=['fix   delete its %d snapshot(s) first:'%len(mines),'        '+_clip(_s,64)]+['        '+x for x in _snap_argv(mines)]
            if kids:
                _k=', '.join((E[k].get('label')or k[:8])for k in kids[:4])
                m+=['  clone children go first: '+_clip(_k,40)]+['    csb kill %s'%k for k in kids[:4]]
            m+=['      then clean the node:','        csb clean %s'%gid]
            die(3,'\n'.join(m))
        _lb=e.get('label')or gid[:8]
        if o.get('dry-run'):
            if is_json(o):out_json({'dry_run':True,'action':'remove ghost node %s'%_lb})
            else:print('dry-run: remove ghost node %s (local record only) - nothing was changed'%_lb)
            return 0
        if not confirm(o,'clean ghost node %s? (local record only)'%_lb,why='cleaning ghost node %s'%_lb):
            return 1
        del E[gid];_REG_DEL.add(gid);save_reg(c)
        if is_json(o):out_json({'cleaned':gid,'label':arg,'kind':'ghost','snapshots':0})
        else:print('%s ghost node removed'%(e.get('label')or gid[:8]))
        return 0
    ext=[i for i in set(list(orig.values())+[(e2 or{}).get('origin')for e2 in led(c).values()])
         if i and i!=arg and not(i in E)and not any(x['id']==i for x in sbs)and i.startswith(arg)]
    if ext or (not any(x['id']==arg for x in sbs) and arg not in E and any(v==arg for v in orig.values())):
        gid2=(ext or[arg])[0];mines=_sids_for(c,gid2,orig)
        m=['clean refused: %s is an [E] node - csb never named it.'%gid2[:8]]
        if mines:
            m+=['  delete its %d snapshot(s) first:'%len(mines)]+['    '+x for x in _snap_argv(mines)]
        else:
            m+=['  nothing points at it - refresh the tree and it is gone']
        die(3,'\n'.join(m))
    snaps=[]
    try:
        snaps=[(s.snapshot_id if hasattr(s,'snapshot_id')else s.get('snapshotID'),
                getattr(s,'names',None)or(s.get('names')if isinstance(s,dict)else[])or[])for s in _val(o,'reading the snapshots',lambda:_fetch_snaps(c))]
    except Exception:pass
    hit=[i for i,ns in snaps if i==arg or arg in ns]or([arg]if arg in led(c)else[])
    if hit:
        o2=dict(o);o2['_']=[arg]
        return cmd_snaprm(o2,c,who='clean')
    brk=next((i for i,e in E.items()if(e or{}).get('broken')or((e or{}).get('parent')and i==arg)),None)
    if brk or any((e or{}).get('label')==arg for e in E.values()):
        i0=brk or next(i for i,e in E.items()if(e or{}).get('label')==arg)
        if o.get('dry-run'):
            if is_json(o):out_json({'dry_run':True,'action':'clear lineage residue of %s'%arg})
            else:print('dry-run: clear lineage residue of %s - nothing was changed'%arg)
            return 0
        E[i0].pop('parent',None);E[i0].pop('broken',None);save_reg(c)
        if is_json(o):out_json({'cleaned':i0,'kind':'lineage'});return 0
        print('%s lineage residue cleared (local registry only)'%arg);return 0
    die(2,'clean: %r not found'%arg)
def _adopt_all(o,c):
    sbs=_val(o,'reading the sandboxes',lambda:fetch_sbs(c))
    todo=[s for s in sbs if not s.get('label')]
    if not todo:
        if is_json(o):out_json({'adopted':[]})
        else:print('adopt --all: nothing to adopt - every live sandbox already has a csb label')
        return 0
    if o.get('dry-run'):
        if is_json(o):out_json({'dry_run':True,'action':'adopt %d sandbox(es)'%len(todo)})
        else:
            print('dry-run: adopt %d sandbox(es) - nothing was changed'%len(todo))
            for s in todo:print('  %s  %s  %s'%(s['id'][:8],s.get('state')or'?',s.get('tpl')or'?'))
        return 0
    if not is_json(o):
        print('ADOPTABLE SANDBOXES')
        for s in todo:print(ckv(s['id'][:8],'%s  %s'%(s.get('state')or'?',s.get('tpl')or'?')))
    done=[];failed=[]
    for s in todo:
        o2=dict(o);o2['_']=[s['id']];o2.pop('all',None)
        try:
            if is_json(o):
                o2.pop('o',None)
                with contextlib.redirect_stdout(sys.stderr):
                    r=cmd_adopt(o2,c)
            else:r=cmd_adopt(o2,c)
            if r==0:done.append(s['id'])
            else:failed.append(s['id'])
        except SystemExit:failed.append(s['id'])
    if is_json(o):out_json({'adopted':done,'failed':failed})
    else:
        print('adopt --all: %d adopted, %d failed'%(len(done),len(failed)))
        if failed:
            print('failed:')
            for x in failed:print('  %s'%x[:8])
            print('fix   run them one by one to see why: csb adopt <sandbox-id>')
    return 0 if not failed else 3
def cmd_adopt(o,c):
    c0=c
    if o.get('all'):return _adopt_all(o,c)
    if o.get('undo'):
        dry_only(o,'undo the auto-adopted records',why='undoing the auto-adopt')
        dead=auto_adopt_undo(c)
        if is_json(o):out_json({'undone':len(dead)})
        else:print('undo: %d auto-adopted record(s) dropped%s'%(len(dead),''if dead else' (there were none)'))
        return 0
    arg=need_arg(o,'adopt: <id>   (or: adopt --all)')
    dry_only(o,'adopt %s'%arg)
    sbs=_val(o,'reading the sandboxes',lambda:fetch_sbs(c));E=reg(c)['entries']
    hit=[s for s in sbs if s['id']==arg]
    if not hit:
        _nm=[s for s in sbs if s.get('label')==arg]
        if _nm:die(2,'%s is a name, not an id - sandbox targets take the full id now:  %s'%(arg,'  '.join(sorted(str(s['id'])for s in _nm))))
        if arg.startswith('snap-'):
            die(2,'adopt: %s is a snapshot\nfix   csb start %s --label <fam>_<NN>'%(arg,arg))
        u=[s for s in sbs if not s.get('label')]
        die(2,'adopt: no match for %r\nfix   unnamed now:  %s'%(arg,', '.join(s['id'][:8]for s in u[:6]))if u else die(2,'adopt: no match for %r'%arg))
    s=hit[0]
    if s['id'] in E and (E[s['id']]or{}).get('label'):
        die(2,'adopt: %s already carries the csb label %r - nothing to do'%(s['id'],E[s['id']]['label']))
    tpls=tpl_rows(c);al=next((t['alias']for t in tpls if t['id']==s.get('tpl')),None)
    fam=o.get('family')or s.get('family')or(DATE_TPL.sub('',al or'')or'')
    if not fam:die(2,'adopt: cannot infer a family - its template id %r has no alias. pass --family NAME'%s.get('tpl'))
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,64}',fam):die(2,'adopt: bad family %r (use [A-Za-z0-9_-]{1,64})'%fam)
    ns=nseq_next(E,reg(c)['family_highwater'],fam)
    lab=o.get('as')or(o.get('label'))or label_default(fam,ns)
    bad=label_err(lab,fam,E)
    if bad:die(2,'adopt: label %r rejected (%s)'%(lab,bad))
    reg(c)['family_highwater'][fam]=max(reg(c)['family_highwater'].get(fam,0),ns)
    E[s['id']]={'label':lab,'family':fam,'kind':'start','parent':fam,'nseq':ns,
                'ts':s.get('ts')or _now(),'adopted':True}
    save_reg(c)
    mines=_sids_for(c,s['id'])
    if is_json(o):out_json({'sandbox_id':s['id'],'label':lab,'family':fam,'nseq':ns,'snapshots':mines,'server_metadata':False})
    else:
        print('adopted %s  (was %s)'%(lab,s['id'][:8]))
        print(ckv('label',lab))
        print(ckv('family',fam))
        print(ckv('sandbox',s['id']))
        print(ckv('placement','[T] %s root - it has a name now (an unnamed template shows as [T] tpl-xxxxxxxx)'%fam))
        print(ckv('snapshots','%d moved under it too'%len(mines)if mines else'none'))
        for x in mines[:4]:print('  %s  %s'%(' '*CKVW,x))
        print('')
        print('  note: the server has no metadata-update endpoint (only PUT')
        print('        network / PUT template alias), so csb.* was NOT written')
        print('        back - this name lives in the local ledger:')
        print('        %s'%c['reg'])
    return 0
def cmd_admin(o,c):
    tail=o.get('tail')
    if not tail:
        if not is_tty():die(2,'admin: pass official command after -- (see help)')
        import readline
        try:tail=[input('official cmd: ').strip()]
        except EOFError:return 1
        if not tail[0]:return 1
    if is_json(o):die(2,"admin runs the official CLI verbatim - csb's -o json does not apply (use the official flag)")
    argv=[str(x) for x in (tail if isinstance(tail,list) else[tail])]
    if not argv:return 1
    dry_only(o,'run the official command: %s'%' '.join(argv),why='running the official CLI verbatim')
    if os.path.basename(argv[0])in('cubemastercli','cubemaster')and not any(a=='-a'or a.startswith('-a=')or a.startswith('--address')for a in argv[1:]):
        argv=[_env('CSB_CUBEMASTERCLI')or argv[0]]+cm_addr()+argv[1:]
    try:
        p=subprocess.run(argv)
    except FileNotFoundError:
        die(3,'admin: pass the words after --\nfix   csb admin -- <cmd>          (pipes: csb admin -- sh -c \'<line>\')')
    if p.returncode:err('admin: %s exited %d'%(argv[0],p.returncode))
    return 0 if p.returncode==0 else 3
def _Vol():return _sb_mod().Volume
def _vol_who(users,limit=3):
    return', '.join('%s (%s)'%(l,short_id(i))for l,i in users[:limit])+(' ... and %d more'%(len(users)-limit)if len(users)>limit else'')
def _vol_holders(c,o=None):
    try:raw=_val(o or{},'checking who mounts each volume',lambda:_Sandbox().list_v2(config=sdk(c)))
    except (Exception,SystemExit):return{}
    _r=reg(c)['entries'];out={}
    for x in raw:
        s=sb_from_raw(x,_r)
        nm=((s.get('label')or'').strip()or short_id(s['id']))
        for v in(s.get('vols')or[]):out.setdefault(v,[]).append((nm,s['id']))
    return out
def vol_rows(c):
    vs=_Vol().list(config=sdk(c))
    hold=_vol_holders(c)
    out=[]
    for v in vs:
        vid=v.volume_id if hasattr(v,'volume_id') else v.get('volumeID')
        nm=(v.name if hasattr(v,'name') else v.get('name'))or vid
        _u=hold.get(nm)or hold.get(vid)or[]
        out.append({'name':str(nm or vid),'id':str(vid or nm),'refcount':len(_u),
                    'mounted_by':[{'label':l,'sandbox_id':i} for l,i in _u]})
    return out
def cmd_vol_ls(o,c):
    try:rows=_val(o,'listing the volumes',lambda:vol_rows(c))
    except Exception as ex:die(3,'Volume.list failed: %s\nfallback: cubemastercli vol ls (backend may be down)'%ex)
    if is_json(o):out_json([{'volume_id':r['id'],'name':r['name'],'refcount':r['refcount'],'mounted_by':r['mounted_by']} for r in rows]);return 0
    if not rows:print('(no volumes - create one:  csb vol create <name>, then mount it at start with --vol /data:<name>)')
    else:
        for r in rows:
            _w=_vol_who([(x['label'],x['sandbox_id'])for x in r['mounted_by']])or'unmounted'
            _c=int(r['refcount'])
            print('%-18s %d mount%s   %s'%(r['name'],_c,''if _c==1 else's',_w))
    return 0
def cmd_vol_create(o,c):
    name=need_arg(o,'vol create: <name> [--driver NAME]')
    drv=o.get('driver')
    if o.get('dry-run'):
        _w='create volume %s%s'%(name,(' (driver %s)'%drv) if drv else '')
        if is_json(o):out_json({'dry_run':True,'action':_w})
        else:sys.stdout.write('dry-run: %s - nothing was changed\n'%_w)
        return 0
    try:vol=_val(o,'creating the volume %s'%name,lambda:_Vol().create(name,driver=drv) if drv else _Vol().create(name))
    except Exception as ex:die(3,'Volume.create failed: %s\nfallback: cubemastercli vol create %s'%(ex,name))
    vid=vol.volume_id if hasattr(vol,'volume_id') else str(vol)
    if is_json(o):out_json({'volume_id':vid,'name':name,'note':'volume = a filesystem outside every sandbox; name fixed; snapshots hold no volume data. see: csb help vol'})
    else:
        print('volume created')
        if not o.get('quiet'):vol_warn_short()
    return 0
def cmd_vol_mount(o,c):
    if is_json(o):die(2,'vol mount never mounts - recreate:  csb start <template> --vol <path>:<volume>')
    if len(o['_'])<2:die(2,'vol mount: <id>:<path> <volID|name> [ro]')
    obj=o['_'][0];vol=o['_'][1];ro='ro' in o['_'][2:]
    l,p=_split_obj(o,obj)
    tok,why=vol_mount_arg(p,vol,ro,vol_known(c))
    if why:die(2,'vol mount %s: %s'%(vol,why))
    vol_warn()
    die(2,'mount only possible at create time (the SDK has no live attach) - a volume goes on at start\nfix   recreate it:  csb start %s --vol %s'%(l or '<alias>',tok))
def _vol_users(c,arg,o=None):
    try:raw=_val(o or{},'checking who holds the volume %s'%arg,lambda:_Sandbox().list_v2(config=sdk(c)))
    except Exception:return[]
    _r=reg(c)['entries'];out=[]
    for x in raw:
        s=sb_from_raw(x,_r)
        if arg in(s.get('vols')or[]):
            _ent=_r.get(s['id'])or{}
            lab=str(_ent.get('label')or s.get('label')or'').strip()or short_id(s['id'])
            out.append((lab,s['id']))
    return out
def _vol_busy(arg,users):
    who=', '.join('%s (%s)'%(l,short_id(i))for l,i in users[:5])
    if len(users)>5:who+=' ... and %d more'%(len(users)-5)
    if not who:who='the platform still counts live holders'
    ids=' '.join(i for _l,i in users[:5])or'<sandbox>'
    first='vol rm refused: %s mounted by %d %s'%(arg,len(users),'sandbox'if len(users)==1 else'sandboxes')
    return('\n'.join([first,
                       '  mounted by  %s'%who,
                       '  fix   csb kill %s --yes   (a mounted volume cannot be deleted)'%ids,
                       '  then  csb vol rm %s --yes   (the files stay)'%arg]))
def cmd_vol_rm(o,c):
    if len(o['_'])<1:die(2,'vol rm: <volID|name> [--yes]')
    arg=o['_'][0]
    if not VOL_ID_RE.match(arg):die(2,'bad volume id: %s (letters, digits, _ and - only, up to 128)'%arg)
    _u=_vol_users(c,arg,o)
    if _u:die(3,_vol_busy(arg,_u))
    if not confirm(o,'delete volume %s? (irreversible - the files in it go with it)'%arg,why='deleting volume %s'%arg):return 1
    try:ok=_val(o,'deleting the volume %s'%arg,lambda:_Vol().destroy(arg),hint='  csb vol ls shows the live list')
    except Exception as ex:
        _s=str(ex)
        if '130409' in _s or'in use by' in _s:die(3,_vol_busy(arg,_u))
        if '404' in _s:die(2,'unknown volume: %s (see csb vol ls)'%arg)
        die(3,'Volume.destroy failed: %s'%ex)
    if ok is False:die(2,'unknown volume: %s (see csb vol ls)'%arg)
    if is_json(o):out_json({'volume_id':arg,'deleted':True})
    else:print('deleted volume %s'%arg)
    return 0
def cmd_label_reset(o,c):
    fam=need_arg(o,'label-reset: <family> [--start N]')
    n=_int(o.get('start'),1,'--start')
    if n<0:die(2,'--start must be >=0, got %d'%n)
    if re.fullmatch(r'tpl-[0-9a-f]{24}',fam):
        _al=next((t.get('alias')for t in tpl_rows(c)if t.get('id')==fam and t.get('alias')),None)
        if _al:
            err('label-reset: %s is a template id - resetting the family %s instead'%(fam,_al));fam=_al
    _orig=fam
    _f2=tpl_family(c,fam)
    _alias=None
    try:
        _cand=next((t.get('alias')for t in tpl_rows(c)if (t.get('alias')or'')==_orig and not t.get('is_snap')),None)
        if _cand and (reg(c).get('family_highwater')or{}).get(_cand)is not None:_alias=_cand
    except Exception:_alias=None
    if _alias:
        err('label-reset: %s is a template alias - resetting its own numbering (%s)'%(_orig,_alias))
        fam=_alias
    elif _f2!=fam:
        err('label-reset: template %s starts into family %s - resetting family %s instead'%(fam,_f2,_f2));fam=_f2
    _fam_known=fam in (reg(c).get('family_highwater')or{})or any((e or{}).get('family')==fam for e in reg(c)['entries'].values())or any((e or{}).get('fam')==fam for e in led(c).values())or any((t.get('alias')or'')==fam or (t.get('alias')or'').startswith(fam+'-')for t in tpl_rows(c))or any(s.get('family')==fam for s in fetch_sbs(c))
    if not _fam_known:
        err('label-reset: %s is a new family - numbering will be set as asked'%fam)
    alive=[s for s in fetch_sbs(c) if s.get('family')==fam or str(s.get('label')or'').split('_')[0]==fam]
    if alive:
        _labs=sorted((s.get('label')or s['id'])for s in alive)
        die(3,'label-reset: %s has %d sandbox(es)\nfix   csb kill %s --yes'%(fam,len(_labs),' '.join(s['id']for s in alive)))
    lsnp=[(sid,(e.get('name')or sid[:8])) for sid,e in led(c).items() if e.get('fam')==fam]
    if lsnp:
        die(3,'label-reset: %s has %d snapshot(s)\nfix   csb snaprm %s --yes'%(fam,len(lsnp),
              ' '.join(sid for sid,_ in lsnp)))
    _fs=short_id(fam)if fam.startswith('tpl-')else fam
    if not confirm(o,'reset numbering for %s (next label %s_%02d)? [destructive]\nWHY   the family has no live sandbox, template or ledger entry\nFIX   answer y to create the family at the next number'%(fam,_fs,max(n,1)),why='resetting family %s numbering'%fam):return 1
    reg(c)['family_highwater'][fam]=n-1;save_reg(c);_hw_set(c['reg'],{fam:n-1})
    _junk=[k for k in(reg(c).get('family_highwater')or{})if re.fullmatch(r'tpl-[0-9a-f]{24}',str(k))]
    if _junk:
        _m=_hw_read(c['reg'])
        for k in _junk:
            _m.pop(k,None);reg(c)['family_highwater'].pop(k,None)
        _hw_save(c['reg'],_m)
    if is_json(o):out_json({'family':fam,'next_default':max(n,1),'highwater':max(n,1)-1})
    else:print('numbering reset  ->  next label %s_%02d'%(_fs,max(n,1)))
    return 0
def _treefix(nodes):
    ks=set()
    def walk(ns):
        for n in ns:
            ks.update(n.keys())
            walk(n.get('children')or[])
    walk(nodes)
    def fill(ns):
        for n in ns:
            for k in ks:n.setdefault(k,None)
            fill(n.get('children')or[])
    fill(nodes);return nodes
def cmd_tree(o,c):
    sbs,tps,org=_val(o,'reading the cluster',lambda:(fetch_sbs(c),tpl_rows(c),fetch_snap_origins(c)),
                     hint='  csb ls is the same list without the snapshots')
    tree=build_tree(sbs,tps,reg(c),led(c),org)
    seen_mark(c,sbs,org)
    if is_json(o):out_json(_treefix(tree));return 0
    _render_tree(tree,on=color_ok(c))
    return 0
def _c(code,text,on):
    return('\033[%sm%s\033[0m'%(code,text))if on else text
def _allnodes(nodes,out=None):
    out=[] if out is None else out
    for n in nodes:
        out.append(n);_allnodes(n.get('children')or[],out)
    return out

def _render_tree(nodes,ind=0,on=False,parent=False):
    pad='  '*ind
    if ind==0:_dupmark(_allnodes(nodes))
    for n in nodes:
        k=n.get('kind');lab=n.get('label')or n.get('id')or''
        if lab==n.get('id'):lab=short_id(lab)
        if n.get('_dup'):lab='%s #%s'%(lab,short_id(n.get('id')or''))
        if k in('tpl-root','snap-root','snap','unreg','stale','dead'):
            mark='[%s]'%_TUI.tui_glyph(n)
            st=n.get('state')or('external' if k=='dead' and n.get('external') else('deleted' if k=='dead' else('stale' if n.get('stale') else('orphan' if n.get('orphan')else''))))
            line='%s%s %s'%(pad,mark,_c('1',lab,on))
            if _TUI.tui_tag(n):line+=' (%s)'%_TUI.tui_tag(n)
            if st:line+=' (%s)'%st
            print(line)
        else:
            st=n.get('state')or''
            line='%s%s %s'%(pad,'[%s]'%_TUI.tui_glyph(n),_c('1',lab,on)if n.get('orphan')or n.get('stale')else lab)
            if st:line+=' (%s)'%st
            print(line.rstrip())
        if n.get('children'):_render_tree(n['children'],ind+1,on,True)
HELP_SPEC=(
 ('sec','sandbox:',(
   'ls | start <tpl|alias|snap> [--n N --concurrency M --env K=V]',
   'start: --timeout S --on-timeout kill|pause (0=now -1=never)',
   'start --label L --n N: L_01 ... L_0N; one sandbox keeps L',
   '--vol p:v[ro] --net on|off  (on needs --allow-out|--proxy)',
   '        --no-dns (whitelist: keep DNS blocked; default is auto)',
   '--family <alias>: from-snapshot naming family (clone continues)',
   '--allow-dns: default; --no-dns = whitelist DNS blocked',
   '--driver (vol create): SDK driver; platform default if omitted',
   '        (snapshots keep no volume data)',
   'clone <id...> [--n N] | commit <id> [--alias N]',
   'kill <id...> | info | pause [--all] | resume | url [port]',
   'resume --timeout <sec>  replace the idle TTL from now, one sandbox',
   'net <id> --allow-out <cidr|domain>[,...]',
   '        | --allow-out all | --net off',
   '    (whole-policy replace: a whitelist also sets deny 0.0.0.0/0,',
   '    keeps the sandbox DNS resolver; --dry-run prints the body;',
   '    all IPv4 = --allow-out all; needs a RUNNING sandbox)',
   'timeout <id...> <s> (0=now -1=never)',
   'pause --all prints every target before it pauses anything',
   'sandbox targets are FULL ids (any number of them); names are for start/--label',
   )),
 ('sec','bulk:',(
   'clone/kill/pause/resume/timeout/snaprm all take a list of full ids',
   'start/clone --n: 1..20 direct, >20 double-confirm ([y/N] on tty;',
   'non-tty needs --yes; json is not consent)',
   )),
 ('sec','session:',(
   'shell <id> [-- cmd...] | exec <id...> [--env K=V] -- cmd...',
   'logs [N] | int [-- pattern] [--sig TERM|KILL|HUP|INT|QUIT]',
   'logs: last 200 by default; clock noise filtered (--all)',
   )),
 ('sec','files:',(
   'cp <local> <id>:<path> | cp <id>:<path> <local>',
   'ls-file <id>:<path> (= ls <id>:<path>) | mk',
   'mv | rm | watch',
   'one object each: <id>:<path> (bare id = /, 2nd positional = error)',
   )),
 ('sec','snap:',(
   'snap <id> [name] | rb [id] <id> | snaps | snaprm <id>',
   'after a sandbox: the full id; alone: id or name finds the sandbox',
   'snaprm takes ONE id: a name that matches several lists them',
   'snaprm refused: a snapshot the tree still references, or a live',
   'clone that needs one more ask - --force deletes either way',
   '130409 = snapshot still held by a live clone (retry 8x3s)',
   )),
 ('sec','kill:',(
   'one confirm; its snapshots are NEVER deleted - they stay as',
   'a [D] node for a sandbox you killed (d clears it)',
   )),
 ('sec','volume:',(
   'attach at create time only (--vol <path>:<vol>[ro]); no live',
   'detach - pause detaches the node mount, resume re-attaches;',
   'data lives until vol rm. snap/clone/commit are allowed - the',
   'snapshot keeps rootfs and memory only, never the volume data',
   )),
 ('sec','tpl:',(
   'tpl ls|info|alias|rm | tpl build --image <ref> --alias NAME',
   'tpl clean-hw [--yes]: drop unreachable high-water keys',
   '[--disk 1G] [--mem 500M] [--cpu 1000] [--allow-out <cidr>]',
   '        [--deny-out <cidr>] [--no-internet]',
   'tpl doctor [--fix] [--probe A] [--node H]: can a sandbox start?',
   'read-only by default; --probe <alias> tries one template',
   'and on 130483 --fix redoes only the template this run probed',
   'names: a sandbox name is permanent, and so is a snapshot name -',
   'only',
   'template aliases are renamable (tpl alias). family NN is an auto',
   )),
 ('sec','admin:',(
   'admin -- <official cmd>; the words after -- go straight to the',
   'program, no shell. A leading cubemastercli gets',
   '-a 127.0.0.1 -p 8089; CSB_CUBEMASTER_HOST / _PORT override',
   )),
 ('sec','adopt:',(
   'adopt <id> [--as NAME] | adopt --all - takes in',
   'objects csb did not create (a nameless sandbox or template)',
   'a snapshot is not named: start a sandbox from it instead',
   'csb adopt --undo - drop what the first-run auto-adopt wrote',
   )),
 ('sec','clean:',(
   'clean <id> = drop [D] / [E] / stale nodes once nothing holds',
   'them; [X] = a leftover record the server list did not confirm gone',
   'clean --ledger [--hard] = wipe the local ledger (backup first);',
   '--hard also clears snapshots, highwater and templates',
   )),
 ('sec','prune:',(
   'prune [--entries] [--policies] [--dry-run] [--yes]',
   'drops DEAD local records only (entries + sbx policies)',
   'needs a COMPLETE cluster list; live records are never touched',
   'never touches templates or highwater; backup before writing',
   '--entries / --policies narrow it',
   )),
 ('sec','tz:',(
   'tz [-o json] = local vs server clock, ledger timezone drift',
   )),
 ('sec','config:',(
   'config [list [group]] = every switch: value + where it came from',
   'config get <name>     = one switch: value and origin',
   'config set <name> <value> = store it in switches.json',
   '     (the next run picks it up)',
   'config unset <name>   = drop it; back to the built-in default',
   'config where          = the files involved + what is overridden',
   'config path           = just the switches.json path (for scripts)',
   'groups: ui / tui / auto / dev / csb / official',
   'names look like CSB_UI_BOX; the short old names are no longer read',
   )),
 ('sec','reset:',(
   'label-reset <family> [--start N]  (needs 0 sandbox AND 0 snap)',
   )),
 ('sec','e/i:',(
   'e exec = one command, get the output, done',
   'i shell = up to four ways, all picked from a menu:',
   '  1. copy `csb shell <id>` (in tmux: paste from the tmux buffer)',
   '  2. open a tmux / screen window named after the sandbox',
   '  3. open a herdr tab (needs HERDR_ENV=1, herdr on PATH,',
   '     `herdr status` = 0)',
   '  4. just show the command - copy it by hand',
   'no job control in the sandbox: Ctrl-C cannot interrupt a command',
   'use  int <id> -- <pattern>  to SIGTERM it from outside',
   )),
 ('sec','exec:',(
   'fresh /bin/bash -l -c: no state between calls (pipes and',
   'redirects work - send the whole command in one line)',
   )),
 ('sec','clone:',(
   'clone = N live copies of a RUNNING sandbox now (freeze -> temp',
   'snapshot -> N boots -> temp deleted; state copied at clone time)',
   'snap = one frozen point you keep; restore with rb or boot it',
   )),
 ('sec','flags:',(
   '-o json (machine-readable; not consent) | --yes (skip confirm)',
   '--dry-run (print what a destructive command would do, then stop)',
   'help [topic] = manual; -h / --h / --help prints it',
   '--version | _completions (internal)',
   '--all: pause / adopt / logs / cp',
   '--probe: tpl doctor only (opt-in test of the one template named)',
   '--node: tpl doctor --fix only (redo on H; no source ref needs it)',
   'dangerous: --force / --ledger',
   )),
 ('sec','exit:',(
   '0 ok | 1 cancel | 2 usage | 3 runtime/remote',
   '4 terminal went away (TUI) - see tui-error.log',
   )),
 ('sec','Env:',(
   'CUBE_API_URL CUBE_API_KEY CSB_REGISTRY CSB_AUDIT SSL_CERT_FILE',
   'E2B_* legacy SDK names are no longer read - CUBE_* only',
   'display: CSB_UI_BOX=ascii | CSB_UI_NO_SWEEP | CSB_UI_NO_SPLASH',
   'NO_COLOR also turns colour off',
   'waits are seconds, each clamped: CSB_WAIT=240 (start/resume);',
   'CSB_STOP_WAIT=120 (snap/rb/kill/cp), CSB_EXEC_WAIT=600 (exec),',
   'CSB_CONNECT_WAIT=30 (connect), CSB_HTTP_WAIT=30 (read-only',
   'list/fetch); CSB_CONNECT_WAIT=10 shortens the connect wait to 10s;',
   'volumes: --vol /data:<vol>; read-only appends ro to the name, no',
   'colon (/data:<vol>ro); one volume per path',
   'TUI refresh: CSB_FETCH_WAIT=5, CSB_FETCH_GIVEUP=60 (a mute',
   'refresh is dropped and asked again)',
   'a lone Esc stops waiting - the call keeps running on the',
   'platform, so look before retrying:  csb ls / csb snaps',
   )),
)
HELP_TOPICS=(('vol',(
   'a volume is a filesystem outside every sandbox - no host path',
   'vol ls | create <name> | rm <id|name> --yes',
   '  (the name cannot change)',
   'mount at create time only:  csb start <tpl> --vol /data:<vol>',
   'read-only: append ro to the volume NAME (/data:<vol>ro), no colon',
   '(TUI: press s on a node, then pick the volume)',
   'no live attach or detach (PUT .../volume = 404)',
   'snap / clone / commit / rb work: the snapshot holds rootfs +',
   'memory only; clones mount the SAME live volume,',
   'so two writers corrupt it',
   'read out:  csb cp <id>:/data .   drop:  csb kill <id> --yes',
   'for the notes press V, then Enter on a volume',
   'see also:  csb help snap | csb help start',
   )+tuple(('', ) + tuple(l.strip() for l in VOL_WARN if 'more:' not in l))),
  ('snap',(
   'snap <id> [name] | snap ls | snaps | rb [id] <id> | snaprm <id>',
   'snap ls and snaps are the same list',
   '(NAME / ID / FAMILY / STATUS / BACKEND / TS)',
   'a snap is one frozen point you keep; clone is N live copies now',
   'after a sandbox: the full id; alone: id or name finds the sandbox',
   'snaprm takes ONE id: a name that matches several lists them',
   'refused: a snapshot the tree still references, or a live clone',
   'that needs one more ask - --force deletes either way;',
   '130409 = a live clone still holds it (retry 8x3s)',
   'a snapshot never contains the volume data:  csb help vol',
   )),
  ('start',(
   'start <tpl|alias|snap> [--n N] [--concurrency M] [--env K=V]',
   'start: --timeout S --on-timeout kill|pause (0=now -1=never)',
   '--vol <path>:<vol>[ro] (create time only) | --no-net | --async',
   '--family <alias>: from-snapshot naming family (clone continues)',
   '--allow-dns: default; --no-dns = whitelist DNS blocked',
   '--driver (vol create): SDK driver; platform default if omitted',
   'from a snapshot: --vol is refused - the snapshot mounts the',
   'volumes it was taken with, and re-sending them is 400/130400',
   'the run waits for running unless --async (CSB_WAIT, 240s)',
   'see also:  csb help vol | csb help snap',
   )),
  ('int',(
   'int <id> [-- <pattern>] [--sig TERM|KILL|HUP|INT|QUIT]',
   'no pattern: list the processes inside the sandbox',
   'with a pattern: signal matching processes (default SIGTERM)',
   '--force also touches the sandbox-own envd / jupyter',
   'see also:  csb help start',
   )),
 )
HELP_TAIL=('Keep your agents sandboxed.'if _ASC else'(๑˃ᴗ˂)و  Keep your agents sandboxed.')
def help_lines(panel=False,width=None) -> list:
    import textwrap
    _W=width or HELP_W
    _bl=width is not None
    w=10
    def _hwr(s):
        return [x for x in (textwrap.wrap(s,width=_W,break_long_words=_bl,break_on_hyphens=False)or[''])if x]
    out=['csb v%s - CubeSandbox CLI'%__version__] if width is None else \
        _hwr('csb v%s - CubeSandbox CLI'%__version__)
    out+=[' '*w+s for s in(textwrap.wrap('every command, one line each:  csb help',width=_W)or[''])]
    for kind,lab,lines in HELP_SPEC:
        if kind=='blank':out.append('');continue
        for _i,ln in enumerate(lines):
            for _j,seg in enumerate(textwrap.wrap(ln,width=_W,break_long_words=_bl,break_on_hyphens=False)or['']):
                if _i==0 and _j==0:out.append((TUI_SEC if panel else '')+lab.ljust(w)+seg)
                else:out.append(' '*w+seg)
    out+=['']
    if panel:out.append(TUI_CEN+HELP_TAIL)
    elif width is None:out.append(HELP_TAIL)
    else:out+=_hwr(HELP_TAIL)
    return out
def help_now(panel=False) -> list:
    _t=_termw()
    if not _t:return help_lines(panel)
    return help_lines(panel,min(HELP_W,max(12,_t-11)))
def _topic_render(name,panel=False,width=None):
    import textwrap
    ls=next((l for n,l in HELP_TOPICS if n==name),None)
    if ls is None:return None
    _W=width or HELP_W;_bl=width is not None;w=10;out=[]
    for _i,ln in enumerate(ls):
        for _j,seg in enumerate(textwrap.wrap(ln,width=_W,break_long_words=_bl,break_on_hyphens=False)or['']):
            if _i==0 and _j==0:out.append((TUI_SEC if panel else '')+('%s:'%name).ljust(w)+seg)
            else:out.append(' '*w+seg)
    return out
def topic_lines(name,panel=False):
    _t=_termw()
    return _topic_render(name,panel,min(HELP_W,max(12,_t-11))if _t else HELP_W)
def help_topic_keys():return[n for n,_ls in HELP_TOPICS]
HELP='\n'.join(help_lines(False))+'\n'
def cmd_shell(o,c):
    if is_json(o):die(2,'shell is interactive - use  csb exec -o json <id> -- <cmd>')
    if o.get('dry-run'):die(2,'shell: nothing to preview - it opens an interactive terminal\nfix   csb exec <id> --out /tmp/out -- <cmd>  for a non-interactive run')
    label=need_arg(o,'shell: <id> [-- cmd…]');sb,_=_find_sb(label,c)
    if not sb:die(2,_sbnope(label,c))
    _need_run(sb,'csb shell')
    if not is_tty():die(2,'shell needs a tty\nfix   for non-interactive runs: csb exec <id> -- <cmd>')
    import tty,termios,select,threading,signal
    inst=_inst(sb,c)
    try:
        sz=os.get_terminal_size();rows,cols=sz.lines,sz.columns
    except Exception:rows,cols=24,80
    fd=sys.stdin.fileno();old=termios.tcgetattr(fd);_tty_keep(fd,old)
    one=o.get('tail')
    ph=None;_gone=[False]
    def _close_pty():
        if _gone[0]:return
        _gone[0]=True
        try:
            if ph is not None:ph.kill()
        except Exception:pass
    def _on_hangup(sig,frm):
        _close_pty()
        os._exit(128+sig)
    _old_sigs={}
    for _s in (signal.SIGHUP,signal.SIGTERM):
        try:_old_sigs[_s]=signal.signal(_s,_on_hangup)
        except Exception:pass
    try:
        _senv=exec_envs(c,o,sb['id'])
        ph=inst.pty.create(_pty_size(rows,cols),envs=_senv or None,timeout=None)
        tty.setraw(fd,termios.TCSANOW)
        stop=threading.Event()
        def pump():
            try:
                while not stop.is_set():
                    r,_,_=select.select([fd],[],[],0.2)
                    if r:
                        try:data=os.read(fd,4096)
                        except OSError:break
                        if not data:break
                        ph.send_stdin(data)
            except Exception:pass
        th=threading.Thread(target=pump,daemon=True);th.start()
        def on_winch(sig,frm):
            try:
                s=os.get_terminal_size();ph.resize(_pty_size(s.lines,s.columns))
            except Exception:pass
        signal.signal(signal.SIGWINCH,on_winch)
        if one:
            ph.send_stdin(' '.join(str(x) for x in one)+'\n');ph.send_stdin('exit\n')
        try:
            _lim=shell_max();_tot=0;_warned=False
            for chunk in ph:
                if chunk:
                    _b=chunk if isinstance(chunk,bytes)else str(chunk).encode()
                    try:
                        os.write(sys.stdout.fileno(),_b)
                    except OSError:
                        _close_pty();break
                    _tot+=len(_b)
                    if shell_limit_hit(_tot,_lim,_warned):
                        _warned=True
                        try:
                            sys.stderr.write('\n[csb] shell output passed %s - still running; set CSB_SHELL_MAX to change the threshold\n'%_cp_size(_lim))
                            sys.stderr.flush()
                        except Exception:pass
        except KeyboardInterrupt:pass
        finally:
            _close_pty()
            stop.set()
        try:code=ph.wait()
        except Exception:code=0
    finally:
        _close_pty()
        for _s,_h in _old_sigs.items():
            try:signal.signal(_s,_h)
            except Exception:pass
        _tty_back()
    return 3 if code else 0

def _sw_lookup(n):
    s=str(n or '').strip().lower()
    return _SWBY.get(s)or _SWBYL.get(s)
def _sw_names(key):r=_SWM[key];return (r[1],)+tuple(r[2])
def _sw_rows():
    out=[]
    for k,r in _SWM.items():
        v,o=_sw_src(k)
        out.append((k,r[1],v,o,r[6],r[8],r[9],tuple(r[2])))
    return out
_SWORIGIN={'env':'environment variable','file':'switches.json','default':'built-in default'}
def cmd_config(o,c):
    a=list(o.get('_')or[]);sub=(a[0]if a else'list').lower()
    if sub in('list','ls'):
        grp=(a[1].lower()if len(a)>1 else None)
        rows=[x for x in _sw_rows()if not grp or x[4]==grp]
        if grp and not rows:die(2,'config list: no such group %r - groups are ui / tui / auto / dev / csb / official'%grp)
        if is_json(o):
            out_json({'switches':[{'key':k,'name':n,'value':v,'origin':o2,'group':g,'writable':w,'doc':d,'old_names':list(al)}for k,n,v,o2,g,w,d,al in rows],'file':_sw_path()});return 0
        print('%-22s %-24s %-9s %-10s %s'%('KEY','NAME','VALUE','ORIGIN','WHAT IT DOES'))
        for k,n,v,o2,g,w,d,al in rows:
            _suf=''if w else'   (environment only)'
            _pre='%-22s %-24s %-9s %-10s '%(k,n,''if v is None else v,o2)
            _room=120-len(_pre)-len(_suf)
            if len(d)>_room:d=d[:_room-3]+'...'
            print('%s%s%s'%(_pre,d,_suf))
        print('')
        print('stored in: %s'%_sw_path())
        print('precedence: command line flag > environment variable > switches.json > built-in default')
        return 0
    if sub in('prune','gc'):
        die(2,'config prune was replaced by  csb prune\nfix   csb prune --dry-run   (dead entries + dead sbx policies; --entries / --policies narrow it)')
    if sub=='get':
        if len(a)<2:die(2,'config get needs a name - try:  csb config get ui_box')
        key=_sw_lookup(a[1])
        if not key:die(2,'no such switch: %s  (try: csb config list)'%a[1])
        r=_SWM[key];v,o2=_sw_src(key)
        if is_json(o):
            out_json({'key':key,'name':r[1],'old_names':list(r[2]),'value':v,'origin':o2,'group':r[6],'writable':r[8],'doc':r[9]});return 0
        print('%-11s %s'%('name',r[1]))
        print('%-11s %s'%('value',v))
        print('%-11s %s'%('origin',_SWORIGIN.get(o2,o2)))
        print('%-11s %s'%('what',r[9]))
        if r[2]:print('%-11s %s'%('old names',', '.join(r[2])))
        if not r[8]:print('%-11s this one comes from the environment - csb config will not store it'%'note')
        return 0
    if sub=='set':
        if len(a)<3:die(2,'config set needs a name and a value - try:  csb config set ui_box ascii')
        dry_only(o,'config set %s'%' '.join(a[1:]),why='writing switches.json')
        key=_sw_lookup(a[1])
        if not key:die(2,'no such switch: %s  (try: csb config list)'%a[1])
        r=_SWM[key];ok,why=_sw_set(key,' '.join(str(x)for x in a[2:]))
        if not ok:die(2,why)
        _sw_reset_cache();v,o2=_sw_src(key);raw=_sw_data().get(key)
        etxt=_sw_rt(key,v,r)
        if etxt is None:etxt='0' if r[3]=='bool' else(''if v is None else str(v))
        if is_json(o):out_json({'key':key,'name':r[1],'value':v,'stored':raw,'file':_sw_path(),'origin':o2});return 0
        print('%s = %s   (saved to %s)'%(r[1],v if raw is None else raw,_sw_path()))
        if o2=='env':print('note: %s is set in this shell, so it still wins here - the saved value applies to the next shell'%r[1])
        elif o2=='file' and etxt!=str(raw):print('note: %s is clamped to %s by the built-in range'%(r[1],etxt))
        return 0
    if sub=='unset':
        if len(a)<2:die(2,'config unset needs a name - try:  csb config unset ui_box')
        dry_only(o,'config unset %s'%a[1],why='writing switches.json')
        key=_sw_lookup(a[1])
        if not key:die(2,'no such switch: %s  (try: csb config list)'%a[1])
        ok,why=_sw_unset(key)
        if not ok:die(2,why)
        _sw_reset_cache();v,o2=_sw_src(key)
        if is_json(o):out_json({'key':key,'name':_SWM[key][1],'value':v,'origin':o2});return 0
        print('%s falls back to %s (%s)'%(_SWM[key][1],_SWORIGIN.get(o2,o2),v));return 0
    if sub=='where':
        c=c or cfg();p=_sw_path()
        rows=[]
        for k,r in _SWM.items():
            v,o2=_sw_src(k)
            if o2!='default':rows.append((k,r[1],v,o2))
        if is_json(o):
            out_json({'switches_file':p,'switches_file_exists':os.path.exists(p),'state_file':prefs_path(c),
                      'overridden':[{'key':k,'name':n,'value':v,'origin':o2}for k,n,v,o2 in rows]});return 0
        print('%-22s %s%s'%('switches',p,''if os.path.exists(p)else'   (not created yet - everything is on its default)'))
        print('%-22s %s'%('state (memory)',prefs_path(c)))
        print('')
        if not rows:print('nothing is overridden - every switch is on its built-in default')
        else:
            print('OVERRIDDEN   ORIGIN   VALUE')
            for k,n,v,o2 in rows:print('%-22s %-9s %s'%(n,o2,v))
        return 0
    if sub=='path':
        print(_sw_path());return 0
    die(2,'config: unknown subcommand %r - try list / get / set / unset / where / path'%sub)
def cmd_help(o,c):
    if is_json(o):die(2,'help prints the manual itself, so it has no json form\nfix   read it here:  csb help')
    topic=(o.get('_')or[None])[0]
    if topic and topic not in help_topic_keys():
        die(2,'help: no topic %r\n      available topics: %s\nfix   csb help            the whole manual'%(topic,' | '.join(help_topic_keys())))
    if topic:
        sys.stdout.write('\n'.join(topic_lines(topic,True) if _sw('dev_panel') else topic_lines(topic,False))+'\n');return 0
    sys.stdout.write('\n'.join(help_now(True) if _sw('dev_panel') else help_now(False))+'\n');return 0
def cmd_version(o,c):
    if is_json(o):out_json({'version':__version__})
    else:print('csb %s'%__version__)
    return 0
_WORDS=['ls','ls-file','start','clone','commit','kill','info','net','pause','resume','timeout','url','shell','exec','int','logs','cp','mk','mv','rm','watch','snap','rb','snaps','snaprm','clean','prune','adopt','doctor','vol','tpl','admin','tree','label-reset','help','version','--debug','--quiet','--h','--help','tz','--version','_completions','-o','json','config','list','get','set','unset','where','path','--yes','--async','--label','--family','--timeout','--on-timeout','--env','--meta','--vol','--net','--no-net','--proxy','--alias','--n','--concurrency','--driver','--all','--image','--disk','--mem','--allow-out','--cpu','--force','--fix','--sig','--list','--start','build','alias','create','rm','mount','--as','--dry-run','--ledger','--hard','--entries','--policies','--undo','--via','--allow-dns','--no-dns','--dns-server','--deny-out','--no-internet','--probe','--node','node','out','clean-hw']
LABELCH='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-'
def lab_ok(ch):
    return ch in'_-'or ch.isalnum()or unicodedata.category(ch)in('Mn','Mc')
TPLCH='abcdefghijklmnopqrstuvwxyz0123456789-'
R_TPL='template alias: lowercase letters/digits/hyphens 1-64, no tpl-/snap- prefix'
R_SNAP='permanent; Enter=auto csb-<label>_<date>'
R_LABEL='permanent; 1-64 letters/digits/_/-; Enter=auto <family>_<NN>'
def cmd_completions(o,c):
    if is_json(o):die(2,'_completions has no json form - use the default output.')
    sys.stdout.write('\n'.join(_WORDS)+'\n');return 0
def _doctor_redo(tal,node=None):
    n=(' --node %s'%node)if node else''
    return ['env -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY cubemastercli template redo%s %s'%(n,tal[a])
            for a in sorted(tal)]
def _doctor_apply(o,tal):
    import subprocess
    res=[];quiet=is_json(o);node=o.get('node')
    env={k:v for k,v in os.environ.items()if k.lower()not in('http_proxy','https_proxy','all_proxy')}
    for a in sorted(tal):
        cmd=['cubemastercli','template','redo']
        if node:cmd+=['--node',str(node)]
        cmd.append(tal[a])
        if not quiet:print('           running %s'%' '.join(cmd))
        try:r=subprocess.run(cmd,env=env,capture_output=True,text=True,timeout=900)
        except Exception as ex:
            res.append({'alias':a,'rc':None,'error':str(ex)[:140]})
            if not quiet:print('             FAILED %s'%str(ex)[:140])
        else:
            _t=' '.join((r.stdout or r.stderr or '').split())[:160]
            res.append({'alias':a,'rc':r.returncode,'text':_t})
            if not quiet:print('             rc=%d %s'%(r.returncode,_t))
    return res
def _doctor_target(tpls,tal,want):
    """The one template this run may touch: the alias or id the caller named.

    --fix redoes server-side builds, so the target has to be evidence from this run, never
    "every template that happens to carry an alias"."""
    if want in tal:return want,tal[want]
    hit=[t for t in tpls if t['id']==want]
    if not hit:
        die(2,'tpl doctor: no template named %r\n'
              '  aliases here: %s\n'
              '  fix   csb tpl doctor --probe <alias>   start one sandbox from that template'
              %(want,', '.join(sorted(tal))or'(none)'))
    return(hit[0].get('alias')or want,want)
def cmd_tpl_doctor(o,c):
    args=o.get('_')or[]
    if len(args)>1:
        die(2,'tpl doctor: one template per run (got %d)\n  fix   csb tpl doctor --probe <alias>'%len(args))
    want=args[0]if args else None
    if o.get('fix')and not o.get('probe'):
        die(2,'tpl doctor --fix needs a named probe first - nothing was rebuilt\n'
              '  probe    csb tpl doctor --probe <alias>          start one sandbox from that template\n'
              '  repair   csb tpl doctor --probe <alias> --fix    redo only that template, and only\n'
              '           when that probe failed with 130483')
    if o.get('probe')and not want:
        die(2,'tpl doctor --probe needs the one template it may start: csb tpl doctor --probe <alias>')
    tpls=tpl_rows(c);tal={t['alias']:t['id']for t in tpls if t.get('alias')and not t.get('is_snap')}
    alias=tid=None
    if want:alias,tid=_doctor_target(tpls,tal,want)
    dry_only(o,'start one test sandbox from %s, kill it, and report'%(alias or tid)
             if o.get('probe')else'read-only: list the templates and sandboxes, start nothing')
    ok=None;err=''
    if o.get('probe'):
        if not is_tty()and not o.get('yes'):
            die(2,'tpl doctor --probe starts a test sandbox: pass --yes (non-tty)')
        try:
            sb=_Sandbox().create(template=tid,config=sdk(c))
            try:sb.kill()
            except Exception:pass
            ok=True
        except Exception as ex:
            ok=False;err=str(ex)[:200]
    sbs=_val(o,'reading the sandboxes',lambda:fetch_sbs(c));E=reg(c)['entries']
    bad=(ok is False and '130483' in err)
    probed=bool(o.get('probe'))
    rep={'templates':len(tpls),'aliases':sorted(tal),'probe':probed,'tested':tid,'test_ok':ok,'test_error':err,
         'sandboxes':len(sbs),'ledger':len(E),'unknown':len([s for s in sbs if s['id']not in E]),
         'verdict':('node local store lost the templates'if bad else
                    ('ok'if ok else('read-only - no probe was run'if not probed else'untested')))}
    if bad:
        name=alias or tid
        if o.get('fix'):
            if not is_json(o):print('redo       %s (%s) - the only template this run may rebuild:'%(name,tid))
            if not confirm(o,'redo %s on the server?'%name,why='redoing %s'%name):return 1
            rep['redo']=_doctor_apply(o,{name:tid})
            redone=bool(rep['redo'])and all(r.get('rc')==0 for r in rep['redo'])
            if any(r.get('rc')and 'source_image_ref' in(r.get('text')or'')for r in rep['redo']):
                rep['node_hint']=('redo needs a node: csb tpl doctor --probe %s --fix --node <node-ip>'%name)
            if redone:
                try:
                    sb=_Sandbox().create(template=tid,config=sdk(c))
                    try:sb.kill()
                    except Exception:pass
                    rep['reprobe']={'ok':True}
                except Exception as ex:
                    rep['reprobe']={'ok':False,'error':str(ex)[:200]}
        elif not is_json(o):
            print('redo       1 template failed the probe - only a named one may be redone; run:')
            for ln in _doctor_redo({name:tid},o.get('node')):print('             '+ln)
            print('hint       rerun with --probe %s --fix to run that line'%name)
    _fixed=bool(rep.get('reprobe',{}).get('ok'))
    if is_json(o):out_json(rep);return 3 if((bad and not _fixed)or ok is False)else 0
    print(_nump('%s (%d aliased) · %s (%d unknown) · %d ledger'%(_pl(len(tpls),'template','templates'),len(tal),_pl(len(sbs),'sandbox','sandboxes'),rep['unknown'],len(E))))
    if not probed:
        print('probe      not run - add --probe <alias> to start one test sandbox (opt-in; --yes on a pipe)')
        print('verdict    read-only: templates and sandboxes listed, nothing was started')
        return 0
    if ok is False:print('test       start one from %s failed: %s'%(tid,err))
    else:print('test       start one from %s, then kill: ok'%(alias or tid))
    if bad:
        print('verdict    the node local store lost the templates - that is the reboot symptom')
        if not o.get('fix'):
            print('fix        rerun with --probe %s --fix; only %s may be redone'%(name,name))
            return 3
        rp=rep.get('reprobe')
        if rp and rp.get('ok'):
            print('reprobe    start one again after the redo, then kill: ok')
            print('verdict    redo finished; the template works again')
            return 0
        if rp is not None:
            print('reprobe    start one again after the redo failed: %s'%rp.get('error'))
            print('verdict    redo finished but the new probe still failed - see above; rerun csb tpl doctor --probe %s'%name)
            return 3
        if rep.get('node_hint'):print('hint       %s'%rep['node_hint'])
        print('verdict    the redo did not succeed - see rc above')
        return 3
    if ok is False:
        print('verdict    the probe failed, but not with 130483 - see the error above; no redo')
        return 3
    print('verdict    ok')
    return 0
CMDS={
 'ls':{'fn':cmd_ls,'need_label':0},
 'start':{'fn':cmd_start,'need_label':0},
 'clone':{'fn':cmd_clone,'need_label':1,'pick':1},
 'commit':{'fn':cmd_commit,'need_label':1,'pick':1},
 'kill':{'fn':cmd_kill,'need_label':1,'pick':1},
 'info':{'fn':cmd_info,'need_label':1,'pick':1},
 'net':{'fn':cmd_net,'need_label':1,'pick':1},
 'pause':{'fn':cmd_pause,'need_label':1,'pick':1},
 'resume':{'fn':cmd_resume,'need_label':1,'pick':1},
 'timeout':{'fn':cmd_timeout,'need_label':1,'pick':1},
 'url':{'fn':cmd_url,'need_label':1,'pick':1},
 'shell':{'fn':cmd_shell,'need_label':1},
 'exec':{'fn':cmd_exec,'need_label':1},
 'int':{'fn':cmd_int,'need_label':1,'pick':1},
 'logs':{'fn':cmd_logs,'need_label':1,'pick':1},
 'cp':{'fn':cmd_cp,'need_label':1},
 'ls-file':{'fn':cmd_fls,'need_label':1},
 'mk':{'fn':cmd_mk,'need_label':1},
 'mv':{'fn':cmd_mv,'need_label':1},
 'rm':{'fn':cmd_rmf,'need_label':1},
 'watch':{'fn':cmd_watch,'need_label':1},
 'snap':{'fn':cmd_snap,'need_label':1,'pick':1},
 'rb':{'fn':cmd_rb,'need_label':1,'pick':1},
 'snaps':{'fn':cmd_snaps,'need_label':0},
 'snaprm':{'fn':cmd_snaprm,'need_label':0},
 'clean':{'fn':cmd_clean,'need_label':0},
 'prune':{'fn':cmd_prune,'need_label':0},
 'tz':{'fn':cmd_tz,'need_label':0},
 'adopt':{'fn':cmd_adopt,'need_label':0},
 'vol':{'fn':None,'sub':{'ls':cmd_vol_ls,'create':cmd_vol_create,'mount':cmd_vol_mount,'rm':cmd_vol_rm}},
 'tpl':{'fn':None,'sub':{'ls':cmd_tpl_ls,'info':cmd_tpl_info,'alias':cmd_tpl_alias,'build':cmd_tpl_build,'doctor':cmd_tpl_doctor,'rm':cmd_tpl_rm,'clean-hw':cmd_tpl_clean_hw}},
 'admin':{'fn':cmd_admin,'need_label':0},
 'tree':{'fn':cmd_tree,'need_label':0},
 'label-reset':{'fn':cmd_label_reset,'need_label':0},
 'config':{'fn':cmd_config,'need_label':0},
 'help':{'fn':cmd_help,'need_label':0},
 '_completions':{'fn':cmd_completions,'need_label':0},
}
def _fileobj_present(o):return any(':' in x for x in o.get('_',[]))
def _tty_pick_label(o,c):
    sbs=fetch_sbs(c)
    if not sbs:die(2,'no sandboxes exist (start one first)')
    if is_tty():
        for i,s in enumerate(sbs,1):print('%2d) %s %s %s'%(i,s['label']or'(no name)',s['state'],s['id'][:8]))
        try:r=input('pick 1-%d> '%len(sbs))
        except EOFError:die(1,'cancelled')
        if not r.isdigit()or not 1<=int(r)<=len(sbs):die(1,'cancelled')
        return sbs[int(r)-1]
    die(2,'no label: pass one, or run it on a terminal to pick (csb ls lists them)')

LOGO = r'''_________/\\\\\\\\\______/\\\\\\\\\\\_____/\\\\\\\\\\\\\__
 ______/\\\////////_____/\\\/////////\\\__\/\\\/////////\\\
  ____/\\\/_____________\//\\\______\///___\/\\\_______\/\\\
   ___/\\\________________\////\\\__________\/\\\\\\\\\\\\\\_
    __\/\\\___________________\////\\\_______\/\\\/////////\\\
     __\//\\\_____________________\////\\\____\/\\\_______\/\\\
      ___\///\\\____________/\\\______\//\\\___\/\\\_______\/\\\
       _____\////\\\\\\\\\__\///\\\\\\\\\\\/____\/\\\\\\\\\\\\\/_
        ________\/////////_____\///////////______\/////////////___'''

_BULK=('kill','pause','resume','timeout','clone','snaprm')
_LIST_OWN=('snap','int')
_INBULK=False
_AV=[None]
def bulk_split(cmd,pos):
    if cmd=='timeout':
        if len(pos)<2:return None
        return pos[:-1],[pos[-1]]
    return pos,[]
def _flaglist(o,av=None,labs=None):
    if av is not None:
        _drop=set(labs or[])
        a=[str(x)for x in av[1:]if str(x)not in _drop]
        if o.get('yes')and'--yes'not in a:
            if '--' in a:a.insert(a.index('--'),'--yes')
            else:a.append('--yes')
        return a
    a=[]
    for k,v in o.items():
        if k=='_':continue
        if k=='o':a+=['-o',str(v)]
        elif isinstance(v,bool):
            if v:a+=['--%s'%k]
        elif isinstance(v,list):
            for vi in v:a+=['--%s'%k,str(vi)]
        elif v is not None:a+=['--%s'%k,str(v)]
    return a
def _bulk_multi(cmd,o):
    global _INBULK
    c=cfg();pos=o['_']
    if o.get('o')=='json':die(2,'%s: bulk over %d labels is text-only (-o json is per sandbox; run labels one by one)'%(cmd,len(pos)))
    labs,extra=bulk_split(cmd,pos)
    if labs is None:die(2,'timeout bulk form: csb timeout <id> [<id> ...] <seconds>')
    if cmd=='timeout':
        _te=timeout_err(extra[0]if extra else None)
        if _te:die(2,'timeout: %s'%_te)
    if o.get('list'):
        for _l in labs:
            sys.stdout.write('would %s %s%s\n'%(cmd,_l,(' '+extra[0])if cmd=='timeout'and extra else ''))
        sys.stdout.write('%s - nothing was changed (--list)\n'%_pl(len(labs),'sandbox'if cmd!='snaprm'else'snapshot','sandboxes'if cmd!='snaprm'else'snapshots'))
        return 0
    if cmd=='clone' and int(o.get('n')or 1)>1:die(2,'clone bulk clones each listed source once (use a single label + --n N to fan out)')
    if cmd=='clone':
        for i in labs:
            sb,_=_find_sb(i,c)
            if not sb or sb.get('state')!='running':die(2,'clone bulk needs RUNNING sources: %s is %s\nfix   resume it first:  csb resume %s --yes'%(i,(sb or{}).get('state')or'unknown',(sb or{}).get('id')or i))
    if cmd=='kill' and not(o.get('yes')or o.get('dry-run')):
        _ls=', '.join(labs[:3])+('  ... and %d more'%(len(labs)-3)if len(labs)>3 else'')
        if not is_tty():die(2,'--yes required: killing %s (non-tty)\n  %s'%(_pl(len(labs),'sandbox','sandboxes'),_ls))
        err('kill %s - snapshots are NOT deleted\nfix   csb snaprm <id> --yes\n  %s'
            %(_pl(len(labs),'sandbox','sandboxes'),_ls))
        if not _yn('kill them'):return 1
        o['yes']=True
    rc=0;done=0;res=[];skip=[];_int=False
    _av=_AV[0];_keep=(_JSONMODE[0],_CMDN[0])
    _INBULK=True
    try:
        for lab in labs:
            a=[cmd,lab]+(_flaglist(o,_av,labs)if _av else extra+_flaglist(o))
            _JSONMODE[0]=False;_CMDN[0]=cmd;_STOPWATCH[0]=None
            try:r=main(a)
            except SystemExit as e:r=e.code if isinstance(e.code,int)else 1
            _r2=_STOPWATCH[0]
            if _r2:skip.append((lab,_r2))
            res.append((lab,r))
            if r not in(0,None):rc=3 if r==3 else(rc or r)
            else:done+=1
    except KeyboardInterrupt:
        _int=True
    finally:
        _INBULK=False;_JSONMODE[0],_CMDN[0]=_keep;_STOPWATCH[0]=None
    _sk=dict(skip);_nrun=[lab for lab in labs if lab not in{lab for lab,_r in res}]
    sys.stdout.flush()
    _bad=[(lab,r)for lab,r in res if r and lab not in _sk]
    _no='snapshots'if cmd=='snaprm'else'sandboxes'
    _tail=(' - %d failed'%len(_bad)if _bad else'')+(' - %d not run'%(len(_sk)+len(_nrun))if(_sk or _nrun)else'')
    err('bulk %s: %d of %d %s ok%s'%(cmd,done,len(labs),_no,_tail))
    for lab,_r in _bad[:5]:err('  failed  %s'%lab)
    if len(_bad)>5:err('  ... and %d more'%(len(_bad)-5))
    for lab,_w in list(_sk.items())[:5]:err('  let go  %s  (%s)'%(lab,'stopped watching'if _w=='stop'else'no answer in time'))
    if _sk or _nrun:
        err('  still working: %s'%(', '.join(list(_sk)[:5]+_nrun[:5])))
        err('  the platform keeps working - check first\nfix   csb snaps / csb ls')
    if _int:err('  Ctrl-C stopped the batch here%s'%('; the ones already done are the ones listed as ok above'if done else''))
    if _bad:
        _fl=' '.join(_flaglist(o,_av,labs)if _av else extra+_flaglist(o))
        err('  retry just those:  csb %s %s%s'%(cmd,' '.join(shlex.quote(l)for l,_r in _bad),(' '+_fl)if _fl else''))
        err('  each failure printed its own reason above')
    return rc or(1 if _int else 0)
def _boot_quiet(fn):
    import io
    _old=sys.stderr;buf=io.StringIO();out=None
    def _keep():
        _t=buf.getvalue()
        if _t.strip():
            errlog_append('=== %s ===\n%s\n'%(time.strftime('%Y-%m-%d %H:%M:%S'),_t.rstrip()))
        return _t
    try:
        sys.stderr=buf
        out=fn()
    finally:
        sys.stderr=_old
        _t=_keep()
    return out,_t
def main(argv=None):
    argv=list(sys.argv[1:] if argv is None else argv)
    _AV[0]=argv
    _sig_install()
    _rcf=cfg()['reg']
    if os.path.isdir(_rcf):
        die(2,'CSB_REGISTRY is a directory (%s) - use %s/sandbox-registry.json'%(_rcf.rstrip('/'),_rcf.rstrip('/')))
    if not argv:
        if not is_tty():die(2,'csb: give me a command - "csb help" lists them')
        _w,_bt=_boot_quiet(lambda:_wiped_warn(cfg()))
        _WIPED[0]=_w or None
        _at=''
        try:_,_at=_boot_quiet(lambda:auto_adopt(cfg()))
        except BaseException:pass
        _bm=' '.join(' '.join(x.split())for x in(_bt,_at)if x and x.strip())
        if _bm:os.environ['CSB_DEV_BOOT_MSG']=_bm
        return _tui(cfg())
    cmd,o=parse(argv);_JSONMODE[0]=is_json(o);_CMDN[0]=cmd
    _leadhelp=cmd in('-h','--h','--help')
    if _leadhelp:cmd='help'
    _bad=[k for k in o if k not in _KNOWN_FLAGS]
    if _bad:
        die(2,'unknown option%s: %s\nfix   csb help lists the commands; flags per command: csb help <command>; put literal text after --'%(
            '' if len(_bad)==1 else's',
            ', '.join(('--%s'%k)if len(k)>1 else('-'+k)for k in _bad)))
    if cmd=='help' or o.get('h') is True:
        _ho=o if _leadhelp or cmd=='help' else {**o,'_':[]}
        return cmd_help(_ho,cfg())
    _sz=[k for k in('disk','mem','cpu')if o.get(k)not in(None,True,'')]
    if _sz and not(cmd=='tpl'and(o['_'][:1]or[''])==['build']):
        die(2,'%s does not take %s\n      these work only with csb tpl build'%(cmd or 'csb',', '.join('--%s'%k for k in _sz)))
    if (o.get('deny-out')or o.get('no-internet')) and not(cmd=='tpl'and(o['_'][:1]or[''])==['build']):die(2,'--deny-out/--no-internet only apply to `csb tpl build`')
    if o.get('allow-out')not in(None,'')and not(cmd=='start'or cmd=='net'or(cmd=='tpl'and(o['_'][:1]or[''])==['build'])):
        die(2,'%s: --allow-out only applies to `csb start` / `csb net` / `csb tpl build`.'%(cmd or 'csb'))
    if cmd=='start'or cmd=='net'or(cmd=='tpl'and(o['_'][:1]or[])==['build']):_allow_out(o)
    if o.get('debug'):sys.stderr.write('debug: csb %s | cmd=%s | registry=%s | ledger=%s\n'%(__version__,cmd or'(none)',_rcf,_sec(_rcf,'led') if 'led' else ''))
    if cmd in('--version','version'):return cmd_version(o,cfg())
    if cmd=='ls' and _fileobj_present(o):
        if len(o['_'])>1:die(2,'ls: one object only - the path belongs after the colon\n  fix   csb ls <id>:<path>')
        return cmd_fls(o,cfg())
    if cmd=='ls' and o.get('_'):
        die(2,'ls: %s is not a file object - add the colon to list files, or drop it to list sandboxes\n  fix   csb ls <id>:<path>'%(o['_'][0],))
    ent=CMDS.get(cmd)
    if ent is None:die(2,'no such command: %s\nfix   csb help    lists all 36 commands'%cmd)
    if 'sub' in ent:
        if not o['_']:
            if cmd=='vol':die(2,'vol: needs a subcommand: ls | create | mount | rm\n     example: csb vol ls')
            die(2,'%s: needs subcommand (%s)'%(cmd,','.join(ent['sub'])))
        sub=ent['sub'].get(o['_'][0])
        if sub is None:
            if cmd=='vol':die(2,'vol: unknown subcommand %s\n     available: ls | create | mount | rm'%o['_'][0])
            die(2,'%s: unknown subcommand %s'%(cmd,o['_'][0]))
        o['_']=o['_'][1:]
        return sub(o,cfg())
    if cmd=='resume' and o.get('timeout') is not None and len(o['_'])>1:
        die(2,'resume --timeout takes one sandbox - run it once per sandbox\nfix   csb resume <id> --timeout <sec>')
    if cmd in _BULK and o.get('list'):o['dry-run']=True
    if o.get('list') and cmd not in _BULK and cmd not in _LIST_OWN:
        die(2,'--list only applies to the bulk commands (%s) and to snap/int, which preview one target\nfix   for a dry-run use --dry-run; to see what it would do, drop --list'%' / '.join(_BULK))
    if cmd in _BULK and len(o['_'])>1 and not _INBULK:
        _bs=bulk_split(cmd,o['_'])
        if _bs and len(_bs[0])>1:return _bulk_multi(cmd,o)
    fn=ent['fn']
    if ent.get('pick') and not o.get('_') and not o.get('all'):
        sb=_tty_pick_label(o,cfg())
        o['_']=[sb['id']]
    return fn(o,cfg())
def _io_hardening():
    for st in(sys.stdout,sys.stderr):
        try:st.reconfigure(errors='replace')
        except Exception:pass
def _run():
    _io_hardening()
    a=sys.argv[1:]
    try:
        try:sys.exit(main())
        except KeyboardInterrupt:sys.exit(1)
    except SystemExit as e:
        _seen_commit_quiet()
        _audit(a,e.code if isinstance(e.code,int) else 1);raise
    except Exception as ex:
        _seen_commit_quiet()
        _audit(a,3)
        name=type(ex).__name__
        import cubesandbox as _m
        base=getattr(_m,'CubeSandboxError',(Exception,))
        _m2='error: %s: %s'%(name,ex)
        if isinstance(ex,base):
            code=getattr(ex,'status_code',None) or getattr(ex,'status',None)
            _m2='error: %s%s: %s'%(name,(' (http %s)'%code)if code else '',ex)
        if _JSONMODE[0]:
            try:out_json(_err_obj(3,_m2,raw=str(ex)))
            except Exception:pass
        sys.stderr.write(_nump(_m2)+_net_hint(str(ex))+'\n');sys.exit(3)
def _tui(c):
    from csb_tui import tui
    return tui(c)

def _pty_size(rows,cols):
    try:
        from cubesandbox import PtySize
        return PtySize(rows,cols)
    except Exception:
        from cubesandbox import Pty
        return Pty.PtySize(rows,cols) if hasattr(Pty,'PtySize') else __import__('cubesandbox',fromlist=['PtySize']).PtySize(rows,cols)

class _TuiProxy:
    def __getattr__(s,k):
        sys.modules.setdefault('csb',sys.modules[__name__])
        try:
            import csb_tui
        except ImportError:
            _d=os.path.dirname(os.path.abspath(__file__))
            if _d not in sys.path:sys.path.insert(0,_d)
            import csb_tui
        return getattr(csb_tui,k)
_TUI=_TuiProxy()

def _autoseen(c,made):
    S=set(x for x in(prefs(c).get('auto_seen')or[])if isinstance(x,str))
    return [x for x in made if x.get('sandbox_id')not in S]
def auto_seen_commit(c=None):
    if not _AUTOPEND:return[]
    c=c or cfg()
    old=[x for x in(prefs(c).get('auto_seen')or[])if isinstance(x,str)]
    S=set(old);nw=[x for x in _AUTOPEND if x not in S]
    if nw:save_prefs(c,auto_seen=(old+nw)[-1000:])
    _AUTOPEND[:]=[]
    return nw
def _seen_commit_quiet():
    try:auto_seen_commit()
    except Exception as _e:_swallow('seen commit',_e)

def _tpl_why(blob,tid):
    low=(blob or '').lower()
    if 'still in use' in low:
        return 'still in use - kill that sandbox first (csb ls); --force does not bypass a live sandbox'
    if 'not found' in low or 'notfound' in low:
        return 'already gone from the server - run it again to drop the local record (%s)'%tid
    if '130483' in low:
        return 'not available locally - csb tpl doctor --probe <alias> --fix (see troubleshooting)'
    last=[l.strip() for l in (blob or '').splitlines() if l.strip()]
    return (last[-1][:160] if last else '')

_PREFW=set();_AUDW=set()
def _prefwarn(p,e):
    if p in _PREFW:return
    _PREFW.add(p);err('warning: cannot save preferences to %s (%s) - the setting did not stick'%(p,e))
def _audwarn(p,what,e):
    k=(p,what)
    if k in _AUDW:return
    _AUDW.add(k);err('warning: cannot %s %s (%s)'%(what,p or'the audit log',e))

_apply_ui()

if __name__=='__main__':_run()


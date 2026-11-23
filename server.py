import asyncio, json, math, os, random, string, time
from aiohttp import web, WSMsgType

W, H, TICK = 1485, 945, 1 / 30
MAX_PLAYERS = 12
ROOMS = {}
WALLS = [
    (0,0,W,18),(0,H-18,W,18),(0,0,18,H),(W-18,0,18,H),
    (250,170,190,42),(620,120,240,46),(980,580,230,46),(430,690,220,42),(900,300,170,38),
    (330,300,130,28),(720,250,170,32),(1120,440,150,30),(520,760,180,28),
    (180,520,42,150),(820,570,42,130),(1260,250,42,130),(560,420,120,26),
    (1030,760,180,28),(90,300,38,125),(1370,500,35,130)
]
WEAPONS = {
 'm4': {'damage':27,'rate':.12,'speed':1050,'mag':30,'reserve':90,'spread':.025},
 'glock': {'damage':22,'rate':.23,'speed':850,'mag':15,'reserve':45,'spread':.035},
 'awp': {'damage':90,'rate':1.05,'speed':1450,'mag':5,'reserve':20,'spread':.008},
 'minigun': {'damage':11,'rate':.06,'speed':980,'mag':120,'reserve':360,'spread':.085},
 'ak47': {'damage':32,'rate':.105,'speed':1080,'mag':30,'reserve':90,'spread':.045},
 'mp5': {'damage':20,'rate':.075,'speed':940,'mag':35,'reserve':105,'spread':.055},
 'shotgun': {'damage':13,'rate':.72,'speed':820,'mag':8,'reserve':40,'spread':.16},
 'deagle': {'damage':48,'rate':.38,'speed':1150,'mag':7,'reserve':35,'spread':.07},
}
RELOAD = {'m4':1.65,'glock':1.25,'awp':2.35,'minigun':3.8,'ak47':1.8,'mp5':1.55,'shotgun':2.2,'deagle':1.6}

def new_room(code, mode):
    return {'code':code,'mode':mode,'players':{},'bullets':[],'created':time.time(),'feed':[],'scores':{'blue':0,'red':0}}

def free_spot(team=None):
    if team == 'blue': return (random.choice([75,120,175]), random.randint(90,H-90))
    if team == 'red': return (random.choice([W-75,W-120,W-175]), random.randint(90,H-90))
    return (random.choice([90,130,185,1300,1350,1390]), random.randint(100,H-100))

def circle_rect(x,y,r,rect):
    rx,ry,rw,rh=rect; qx=max(rx,min(x,rx+rw)); qy=max(ry,min(y,ry+rh))
    return (x-qx)**2+(y-qy)**2 < r*r

def blocked(x,y): return any(circle_rect(x,y,14,a) for a in WALLS)

def clean_name(value):
    value = ''.join(ch for ch in str(value) if ch.isalnum() or ch in ' _-')
    return ' '.join(value.split())[:18] or 'Oyuncu'

async def index(_):
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'index.html')
    if not os.path.isfile(path): return web.Response(text='index.html bulunamadi.', status=500)
    return web.FileResponse(path)

async def ws_handler(req):
    ws=web.WebSocketResponse(heartbeat=25,max_msg_size=4096); await ws.prepare(req)
    room=pid=player=None
    try:
      async for msg in ws:
        if msg.type != WSMsgType.TEXT: continue
        try: data=json.loads(msg.data)
        except (ValueError, TypeError): continue
        if data.get('type') == 'join' and room is None:
            code=''.join(c for c in str(data.get('room','PUBLIC')).upper() if c.isalnum())[:12] or 'PUBLIC'
            mode='tdm' if data.get('mode') == 'tdm' else 'ffa'
            room=ROOMS.get(code)
            if room is None: room=ROOMS.setdefault(code,new_room(code,mode))
            if len(room['players']) >= MAX_PLAYERS:
                await ws.send_json({'type':'error','message':'Oda dolu (en fazla 12 oyuncu).'}); break
            if room['mode'] != mode and room['players']:
                await ws.send_json({'type':'error','message':'Bu oda farklı oyun modunda.'}); break
            pid=''.join(random.choices(string.ascii_letters+string.digits,k=10))
            counts=[sum(1 for e in room['players'].values() if e['p']['team']==t) for t in ('blue','red')]
            team=('blue' if counts[0] <= counts[1] else 'red') if mode=='tdm' else 'none'
            x,y=free_spot(team)
            player={'id':pid,'name':clean_name(data.get('name','Oyuncu')),'team':team,'x':x,'y':y,'hp':100,'armor':100,'alive':True,'angle':0,'weapon':'m4','ammo':{k:v['mag'] for k,v in WEAPONS.items()},'reserve':{k:v['reserve'] for k,v in WEAPONS.items()},'last_shot':0,'reload_until':0,'kills':0,'deaths':0,'input':{}}
            room['players'][pid]={'ws':ws,'p':player}
            await ws.send_json({'type':'joined','id':pid,'room':code,'mode':mode,'map':{'w':W,'h':H,'walls':WALLS,'site':[1130,90,260,210]}})
            continue
        if room is None: continue
        if data.get('type')=='input' and player is None:
            player=room['players'].get(pid,{}).get('p')
        if data.get('type')=='input' and player:
            i=data.get('input') or {}; angle=i.get('angle',player['angle'])
            try: angle=float(angle)
            except (TypeError,ValueError): angle=player['angle']
            if not math.isfinite(angle): angle=player['angle']
            player['input']={'up':bool(i.get('up')),'down':bool(i.get('down')),'left':bool(i.get('left')),'right':bool(i.get('right')),'sprint':bool(i.get('sprint')),'fire':bool(i.get('fire')),'reload':bool(i.get('reload')),'angle':angle,'weapon':i.get('weapon') if i.get('weapon') in WEAPONS else player['weapon']}
    finally:
      if room and pid in room['players']:
        room['players'].pop(pid,None)
        if not room['players']: ROOMS.pop(room['code'],None)
    return ws

async def game_loop(app):
  while True:
    now=time.time()
    for room in list(ROOMS.values()):
      plist=room['players']; bullets=room['bullets']
      for pid,entry in list(plist.items()):
        p=entry['p']; i=p['input']
        if not p['alive']: continue
        p['angle']=i.get('angle',p['angle'])
        w=i.get('weapon',p['weapon'])
        if w in WEAPONS: p['weapon']=w
        speed=315 if i.get('sprint') else 230
        dx=(1 if i.get('right') else 0)-(1 if i.get('left') else 0); dy=(1 if i.get('down') else 0)-(1 if i.get('up') else 0)
        mag=math.hypot(dx,dy)
        if mag: dx/=mag; dy/=mag
        nx=max(32,min(W-32,p['x']+dx*speed*TICK)); ny=max(32,min(H-32,p['y']+dy*speed*TICK))
        if not blocked(nx,p['y']): p['x']=nx
        if not blocked(p['x'],ny): p['y']=ny
        if i.get('reload') and now>=p['reload_until']:
          w=p['weapon']; spec=WEAPONS[w]
          if p['ammo'][w]<spec['mag'] and p['reserve'][w]>0: p['reload_until']=now+RELOAD[w]
          p['input']['reload']=False
        if p['reload_until'] and now>=p['reload_until']:
          w=p['weapon']; need=WEAPONS[w]['mag']-p['ammo'][w]; take=min(need,p['reserve'][w]); p['ammo'][w]+=take; p['reserve'][w]-=take; p['reload_until']=0
        w=p['weapon']; spec=WEAPONS[w]
        if i.get('fire') and now-p['last_shot']>=spec['rate'] and now>=p['reload_until'] and p['ammo'][w]>0:
          p['ammo'][w]-=1; p['last_shot']=now; a=p['angle']; pellets=6 if w=='shotgun' else 1
          for _ in range(pellets):
            pa=a+random.uniform(-spec['spread'],spec['spread'])
            bullets.append({'x':p['x']+math.cos(pa)*22,'y':p['y']+math.sin(pa)*22,'vx':math.cos(pa)*spec['speed'],'vy':math.sin(pa)*spec['speed'],'owner':pid,'damage':spec['damage'],'life':1.4})
      for b in bullets[:]:
        b['x']+=b['vx']*TICK; b['y']+=b['vy']*TICK; b['life']-=TICK
        hit=b['life']<=0 or not (0<b['x']<W and 0<b['y']<H) or any(rx<=b['x']<=rx+rw and ry<=b['y']<=ry+rh for rx,ry,rw,rh in WALLS)
        if not hit:
          for otherid,e in plist.items():
            q=e['p']
            if otherid==b['owner'] or not q['alive']: continue
            shooter=plist.get(b['owner'],{}).get('p')
            if room['mode']=='tdm' and shooter and shooter['team']==q['team']: continue
            if math.hypot(q['x']-b['x'],q['y']-b['y'])<16:
              absorbed=min(q['armor'],b['damage']*.65); q['armor']-=absorbed; q['hp']-=b['damage']-absorbed
              if q['hp']<=0:
                q['hp']=0; q['alive']=False; q['deaths']+=1
                if shooter:
                  shooter['kills']+=1
                  if room['mode']=='tdm': room['scores'][shooter['team']]+=1
                  room['feed'].append({'text':f"{shooter['name']}  ✕  {q['name']}",'team':shooter['team'],'at':now})
                  room['feed']=room['feed'][-5:]
                asyncio.create_task(respawn(q,room['mode']))
              hit=True; break
        if hit: bullets.remove(b)
      state={'type':'state','players':[e['p'] for e in plist.values()],'bullets':bullets,'time':now,'mode':room['mode'],'scores':room['scores'],'feed':[f for f in room['feed'] if now-f['at']<7]}
      dead=[]
      for e in plist.values():
        if e['ws'].closed: dead.append(e['p']['id'])
        else:
          try: await e['ws'].send_str(json.dumps(state,separators=(',',':')))
          except Exception: dead.append(e['p']['id'])
      for d in dead: plist.pop(d,None)
    await asyncio.sleep(TICK)

async def respawn(p,mode):
  await asyncio.sleep(3)
  if mode=='tdm': p['x'],p['y']=free_spot(p['team'])
  else: p['x'],p['y']=free_spot()
  p['hp']=100; p['armor']=100; p['alive']=True

async def on_start(app): app['loop']=asyncio.create_task(game_loop(app))
async def on_stop(app):
  app['loop'].cancel()
  try: await app['loop']
  except asyncio.CancelledError: pass

app=web.Application()
app.router.add_get('/',index); app.router.add_get('/index.html',index); app.router.add_get('/ws',ws_handler)
app.on_startup.append(on_start); app.on_cleanup.append(on_stop)
if __name__=='__main__': web.run_app(app,host='0.0.0.0',port=int(os.environ.get('PORT','8080')))

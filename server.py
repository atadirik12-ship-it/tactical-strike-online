import asyncio, json, math, os, random, string, time
from collections import defaultdict
from aiohttp import web, WSMsgType

W, H = 1485, 945
TICK = 1/30
ROOMS = {}
WALLS = [(0,0,W,18),(0,H-18,W,18),(0,0,18,H),(W-18,0,18,H),
         (250,170,190,42),(620,120,240,46),(980,580,230,46),(430,690,220,42),(900,300,170,38)]
WEAPONS = {
 'm4': {'damage':27,'rate':0.12,'speed':1050,'mag':30,'reserve':90},
 'glock': {'damage':22,'rate':0.23,'speed':850,'mag':15,'reserve':45},
 'awp': {'damage':90,'rate':1.05,'speed':1450,'mag':5,'reserve':20},
 'minigun': {'damage':11,'rate':0.06,'speed':980,'mag':120,'reserve':360},
}

def new_room(code):
    return {'code':code,'players':{},'bullets':[],'created':time.time()}

def free_spot():
    return (random.choice([90,130,185,1300,1350,1390]), random.randint(100,H-100))

def circle_rect(x,y,r,rect):
    rx,ry,rw,rh=rect; qx=max(rx,min(x,rx+rw)); qy=max(ry,min(y,ry+rh))
    return (x-qx)**2+(y-qy)**2 < r*r

def blocked(x,y): return any(circle_rect(x,y,14,a) for a in WALLS)

async def index(_):
    # index.html must be in the same folder as server.py
    html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'index.html')
    if not os.path.isfile(html_path):
        return web.Response(
            text="index.html bulunamadi. index.html dosyasini server.py ile ayni klasore koyun.",
            status=500,
            content_type="text/plain",
        )
    return web.FileResponse(html_path)

async def ws_handler(req):
    ws=web.WebSocketResponse(heartbeat=25, max_msg_size=4096); await ws.prepare(req)
    room=None; pid=''; player=None
    try:
      async for msg in ws:
        if msg.type != WSMsgType.TEXT: continue
        try: data=json.loads(msg.data)
        except Exception: continue
        if data.get('type')=='join' and room is None:
            code=''.join(c for c in str(data.get('room','PUBLIC')).upper() if c.isalnum())[:12] or 'PUBLIC'
            room=ROOMS.setdefault(code,new_room(code)); pid=''.join(random.choices(string.ascii_letters+string.digits,k=10))
            x,y=free_spot(); name=' '.join(str(data.get('name','Oyuncu'))[:18].split()) or 'Oyuncu'
            player={'id':pid,'name':name,'x':x,'y':y,'hp':100,'armor':100,'alive':True,'angle':0,'weapon':'m4','ammo':{k:v['mag'] for k,v in WEAPONS.items()},'reserve':{k:v['reserve'] for k,v in WEAPONS.items()},'last_shot':0,'reload_until':0,'kills':0,'input':{}}
            room['players'][pid]={'ws':ws,'p':player}; await ws.send_json({'type':'joined','id':pid,'room':code,'map':{'w':W,'h':H,'walls':WALLS,'site':[1130,90,260,210]}})
            continue
        if room is None: continue
        if data.get('type')=='input' and player:
            inp=data.get('input',{})
            player['input']={'up':bool(inp.get('up')),'down':bool(inp.get('down')),'left':bool(inp.get('left')),'right':bool(inp.get('right')),'sprint':bool(inp.get('sprint')),'fire':bool(inp.get('fire')),'reload':bool(inp.get('reload')),'angle':float(inp.get('angle',player['angle'])),'weapon':inp.get('weapon',player['weapon'])}
    finally:
      if room and pid in room['players']:
        del room['players'][pid]
        if not room['players']: ROOMS.pop(room['code'],None)
    return ws

async def game_loop(app):
  while True:
    now=time.time()
    for room in list(ROOMS.values()):
      plist=room['players']; bullets=room['bullets']
      for pid,entry in list(plist.items()):
        p=entry['p']; i=p['input'];
        if p['alive']:
          p['angle']=i.get('angle',p['angle'])
          weap=i.get('weapon',p['weapon']);
          if weap in WEAPONS: p['weapon']=weap
          speed=315 if i.get('sprint') else 230; dx=(1 if i.get('right') else 0)-(1 if i.get('left') else 0); dy=(1 if i.get('down') else 0)-(1 if i.get('up') else 0)
          mag=math.hypot(dx,dy)
          if mag: dx/=mag; dy/=mag
          nx=max(32,min(W-32,p['x']+dx*speed*TICK)); ny=max(32,min(H-32,p['y']+dy*speed*TICK))
          if not blocked(nx,p['y']): p['x']=nx
          if not blocked(p['x'],ny): p['y']=ny
          if i.get('reload') and now>=p['reload_until']:
            w=p['weapon']; spec=WEAPONS[w]
            if p['ammo'][w] < spec['mag'] and p['reserve'][w] > 0:
              p['reload_until']=now+({'m4':1.65,'glock':1.25,'awp':2.35,'minigun':3.8}[w])
            p['input']['reload']=False
          if p['reload_until'] and now>=p['reload_until']:
            w=p['weapon']; need=WEAPONS[w]['mag']-p['ammo'][w]; take=min(need,p['reserve'][w]); p['ammo'][w]+=take; p['reserve'][w]-=take; p['reload_until']=0
          w=p['weapon']; spec=WEAPONS[w]
          if i.get('fire') and now-p['last_shot']>=spec['rate'] and now>=p['reload_until'] and p['ammo'][w]>0:
            p['ammo'][w]-=1; p['last_shot']=now; a=p['angle']+random.uniform(-({'m4':.025,'glock':.035,'awp':.008,'minigun':.085}[w]),({'m4':.025,'glock':.035,'awp':.008,'minigun':.085}[w]))
            bullets.append({'x':p['x']+math.cos(a)*22,'y':p['y']+math.sin(a)*22,'vx':math.cos(a)*spec['speed'],'vy':math.sin(a)*spec['speed'],'owner':pid,'damage':spec['damage'],'life':1.4})
      for b in bullets[:]:
        b['x']+=b['vx']*TICK; b['y']+=b['vy']*TICK; b['life']-=TICK
        hit= b['life']<=0 or not (0<b['x']<W and 0<b['y']<H) or any(rx<=b['x']<=rx+rw and ry<=b['y']<=ry+rh for rx,ry,rw,rh in WALLS)
        if not hit:
          for otherid,e in plist.items():
            q=e['p']
            if otherid!=b['owner'] and q['alive'] and math.hypot(q['x']-b['x'],q['y']-b['y'])<16:
              absorbed=min(q['armor'],b['damage']*.65); q['armor']-=absorbed; q['hp']-=b['damage']-absorbed
              if q['hp']<=0:
                q['hp']=0; q['alive']=False
                if b['owner'] in plist: plist[b['owner']]['p']['kills']+=1
                asyncio.create_task(respawn(q))
              hit=True; break
        if hit: bullets.remove(b)
      state={'type':'state','players':[e['p'] for e in plist.values()],'bullets':bullets,'time':now}
      dead=[]
      for e in plist.values():
        if e['ws'].closed: dead.append(e['p']['id'])
        else:
          try: await e['ws'].send_str(json.dumps(state,separators=(',',':')))
          except Exception: dead.append(e['p']['id'])
      for d in dead: plist.pop(d,None)
    await asyncio.sleep(TICK)

async def respawn(p):
  await asyncio.sleep(3)
  p['x'],p['y']=free_spot(); p['hp']=100; p['armor']=100; p['alive']=True

async def on_start(app): app['loop']=asyncio.create_task(game_loop(app))
async def on_stop(app): app['loop'].cancel()

app=web.Application()
app.router.add_get('/', index)
app.router.add_get('/index.html', index)
app.router.add_get('/ws', ws_handler)
app.on_startup.append(on_start)
app.on_cleanup.append(on_stop)
if __name__=='__main__':
  port=int(os.environ.get('PORT','8080')); web.run_app(app,host='0.0.0.0',port=port)

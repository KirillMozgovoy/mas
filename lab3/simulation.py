"""Depot access submodel: independent courier request agents and arbiter."""
import random, statistics, json
from pathlib import Path

def simulate(seed=0, mode='priority', horizon=160, bays=1):
    rng=random.Random(seed)
    jobs=[dict(id=i,courier=i%6,release=i//6*3,duration=rng.randint(2,5),deadline=i//6*3+rng.randint(8,25)) for i in range(60)]
    waiting={}; active={}; done={}; trace=[]; waits=[]; collisions=0
    def msg(t,a,b,k,j):trace.append(dict(time=t,sender=a,receiver=b,kind=k,job=j))
    for t in range(horizon):
        for j,end in list(active.items()):
            if end==t:
                done[j]=t;del active[j];msg(t,f'courier_{jobs[j]["courier"]}','depot','RELEASE',j)
        for j in jobs:
            if j['release']==t:waiting[j['id']]=t;msg(t,f'courier_{j["courier"]}','depot','REQUEST',j['id'])
        # One outstanding service per courier; each courier proposes its oldest job.
        busy={jobs[j]['courier'] for j in active}; candidates=[]
        for c in range(6):
            own=[j for j in waiting if jobs[j]['courier']==c]
            if own and c not in busy:candidates.append(min(own))
        slots=bays-len(active)
        if mode=='uncoordinated':
            # All contenders see the same free capacity; conflicting claims fail.
            if slots>0 and len(candidates)>slots:
                collisions+=1
                for j in candidates:msg(t,'depot',f'courier_{jobs[j]["courier"]}','CONFLICT',j)
                chosen=[]
            else:chosen=candidates if slots>0 else []
        elif mode=='fifo':chosen=sorted(candidates,key=lambda j:(waiting[j],j))[:slots]
        elif mode=='priority':
            # Waiting >=20 takes precedence; otherwise earliest deadline.
            chosen=sorted(candidates,key=lambda j:(0,waiting[j],j) if t-waiting[j]>=20 else (1,jobs[j]['deadline'],j))[:slots]
        else:raise ValueError(mode)
        for j in chosen:
            msg(t,'depot',f'courier_{jobs[j]["courier"]}','GRANT',j)
            waits.append(t-waiting.pop(j));active[j]=t+jobs[j]['duration']
        assert len(active)<=bays
    per=[sum(jobs[j]['courier']==c for j in done) for c in range(6)]
    fairness=sum(per)**2/(6*sum(x*x for x in per)) if sum(per) else 0
    return dict(seed=seed,mode=mode,bays=bays,completed=len(done),pending=60-len(done),
                mean_wait=statistics.mean(waits) if waits else None,max_wait=max(waits,default=None),
                late=sum(done[j]>jobs[j]['deadline'] for j in done),fairness=fairness,
                conflicts=collisions,messages=len(trace),jobs=jobs,trace=trace,completed_ids=done)

def main():
    root=Path(__file__).resolve().parent
    runs=[simulate(s,m,bays=b) for b in (1,2) for s in range(20) for m in ('uncoordinated','fifo','priority')]
    (root/'results.json').write_text(json.dumps([{k:v for k,v in r.items() if k not in ('jobs','trace','completed_ids')} for r in runs],indent=2))
    (root/'traces.json').write_text(json.dumps([r for r in runs if r['seed']==0],indent=2))
    print('120 runs complete')
if __name__=='__main__':main()

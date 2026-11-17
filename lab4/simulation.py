"""Delivery execution protocol fault model; no external systems contacted."""
import json,random
from pathlib import Path
SCENARIOS=('normal','lost_assign','lost_done','crash','forged_done','duplicate_done','stale_done')
def simulate(seed=0, protected=True, scenario='normal', horizon=150):
    if scenario not in SCENARIOS:raise ValueError(scenario)
    rng=random.Random(seed);durations=[rng.randint(2,5) for _ in range(24)]
    state={j:'waiting' for j in range(24)};attempt={j:0 for j in state};assigned={};started={};active={};physical=set();reported=set();trace=[];events=[];dead=set();triggered=False;rejected=0;retries=0;false_reports=0
    def log(t,s,r,k,j,a):trace.append(dict(time=t,sender=s,receiver=r,kind=k,job=j,attempt=a))
    for t in range(horizon):
        for c,(j,a,end) in list(active.items()):
            if end!=t:continue
            del active[c];physical.add(j);log(t,c,'environment','PHYSICAL_DELIVERY',j,a)
            if scenario=='lost_done' and not triggered:triggered=True;log(t,c,'dispatcher','DROP_DONE',j,a)
            else:events.append((t,c,j,a))
            if scenario=='duplicate_done':events.append((t,c,j,a))
        if scenario=='crash' and not triggered and active:
            c=min(active);j,a,end=active.pop(c);dead.add(c);triggered=True;log(t,c,'dispatcher','CRASH',j,a)
        for et,c,j,a in list(events):
            if et!=t:continue
            events.remove((et,c,j,a));log(t,c,'dispatcher','DONE',j,a)
            valid=c==assigned.get(j) and a==attempt[j] and state[j]=='assigned' and j in physical
            if protected and not valid:rejected+=1;continue
            false_reports+=int(j not in physical)
            state[j]='done';reported.add(j)
        if protected:
            for j in state:
                if state[j]=='assigned' and t-started[j]>=8:
                    # Trusted environment receipt closes lost reports without redelivery.
                    if j in physical:state[j]='done';reported.add(j);log(t,'dispatcher','environment','VERIFY_RECEIPT',j,attempt[j])
                    else:
                        c=assigned[j];active.pop(c,None);state[j]='waiting';retries+=1
                        log(t,'dispatcher',c,'REVOKE',j,attempt[j])
        reserved={assigned[j] for j in state if state[j]=='assigned'}
        for c in range(3):
            if c in dead or c in active or c in reserved:continue
            todo=[j for j in state if state[j]=='waiting']
            if not todo:continue
            j=min(todo);attempt[j]+=1;a=attempt[j];state[j]='assigned';assigned[j]=c;started[j]=t
            log(t,'dispatcher',c,'ASSIGN',j,a)
            if scenario=='lost_assign' and not triggered:triggered=True;log(t,'dispatcher',c,'DROP_ASSIGN',j,a)
            else:active[c]=(j,a,t+durations[j])
            if scenario=='forged_done' and not triggered:
                triggered=True;events.append((t+1,'outsider',j,a))
            if scenario=='stale_done' and not triggered:
                triggered=True;events.append((t+1,c,j,a-1))
    return dict(seed=seed,protected=protected,scenario=scenario,physical=len(physical),reported=len(reported),false_success=len(reported-physical),false_reports=false_reports,unreported=len(physical-reported),pending=24-len(reported),retries=retries,rejected=rejected,messages=len(trace),trace=trace,durations=durations)
def main():
    root=Path(__file__).resolve().parent
    runs=[simulate(s,p,c) for s in range(20) for c in SCENARIOS for p in (False,True)]
    (root/'results.json').write_text(json.dumps([{k:v for k,v in r.items() if k not in ('trace','durations')} for r in runs],indent=2))
    (root/'traces.json').write_text(json.dumps([r for r in runs if r['seed']==0],indent=2));print('280 runs complete')
if __name__=='__main__':main()

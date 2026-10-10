/* Native display helpers. Never execute actions or retain private action contents. */
(function(root){
  'use strict';
  const states={queued:'Waiting for a slot',running:'Working',awaiting_review:'Awaiting your review',verifying:'Verifying',done:'Work complete',blocked:'Work stopped',expired:'Review expired',unknown:'Outcome unconfirmed',cancelled:'Cancelled'};
  function steps(events){
    const map=new Map();let legacy=0;
    for(const e of events||[]){
      if(!e||typeof e.label!=='string'||!Object.hasOwn(states,e.state))continue;
      // Legacy histories lack IDs. Pair only their adjacent same-label events.
      const id=e.id||('legacy:'+e.label+':'+(e.state==='running'?++legacy:legacy));
      const seq=Number.isInteger(e.seq)?e.seq:legacy;
      const old=map.get(id);if(old&&old.seq>seq)continue;
      map.set(id,{id,seq,label:e.label,state:e.state});
    }
    return [...map.values()].sort((a,b)=>a.seq-b.seq).slice(-8);
  }
  function progress(events,state){
    const d=document.createElement('details');d.className='work-steps';
    d.dataset.outcome=Object.hasOwn(states,state)?state:'unknown';
    const settled=['done','blocked','unknown','cancelled','expired'].includes(d.dataset.outcome);
    d.open=!settled;if(settled)d.classList.add('settled');
    const summary=document.createElement('summary');const mark=document.createElement('span');mark.className='work-orbit';mark.setAttribute('aria-hidden','true');
    const title=document.createElement('span');title.className='work-heading';title.textContent=states[d.dataset.outcome];summary.append(mark,title);d.append(summary);
    const ol=document.createElement('ol');
    for(const s of steps(events)){
      const li=document.createElement('li');li.dataset.state=s.state;li.dataset.stepId=s.id;li.setAttribute('aria-label',s.label+': '+states[s.state]);
      const icon=document.createElement('span');icon.className='step-mark';icon.setAttribute('aria-hidden','true');icon.textContent=s.state==='done'?'✓':s.state==='blocked'?'!':'·';
      const text=document.createElement('span');text.className='step-label';text.textContent=s.label;li.append(icon,text);ol.append(li);
    }
    d.append(ol);const note=document.createElement('small');note.textContent='Recorded work events. No automatic resend.';d.append(note);return d;
  }
  const api={states,steps,progress};root.CrayonUX=api;
  if(typeof module!=='undefined')module.exports=api;
})(typeof window!=='undefined'?window:globalThis);

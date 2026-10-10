"""User-visible execution summaries only. Never reasoning, prompts, arguments or private results."""
from contextvars import ContextVar
callback=ContextVar('crayon_progress',default=None)
recorded=ContextVar('crayon_work_events',default=None)
def snapshot():return list(recorded.get() or [])[-16:]
LABELS={'web_search':'Searching public sources','read_url':'Reading a public page','research_web':'Checking sources','run_python':'Running a calculation','computer_browse':'Opening the public browser','computer_run':'Running a computer task','create_csv':'Building a CSV','create_bar_chart':'Drawing a chart','create_task':'Saving the requested task','list_tasks':'Reading your tasks','list_reminders':'Reading your reminders'}
def emit(label,state='running',step_id=None):
    events=recorded.get()
    event={'label':label[:80],'state':state}
    if events is not None:
        # Request-local sequence. Repeated tool labels are different steps;
        # settling events explicitly reuse the running step's id.
        if step_id is None:
            step_id='step_'+str(len(events)+1)
        event.update(id=step_id,seq=len(events)+1)
        events.append(event)
    fn=callback.get()
    if fn:
        try:fn(dict(event))
        except Exception:pass
    return step_id

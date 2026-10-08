import threading
import cr_telegram as T

def test_no_progress_after_reply():
    out=T.CaptureOut();guard=T.ProgressOut(out,1,[])
    assert guard.emit('working')
    guard.send(1,'final')
    assert not guard.emit('late')
    assert [x['text'] for x in out.sent]==['working','final']

def test_inflight_progress_serialized_before_final():
    entered=threading.Event();release=threading.Event()
    class SlowOut(T.CaptureOut):
        def send(self,chat,text,markup=None):
            if text=='working':
                entered.set();assert release.wait(2)
            super().send(chat,text,markup)
    out=SlowOut();guard=T.ProgressOut(out,1,[])
    worker=threading.Thread(target=guard.emit,args=('working',));worker.start()
    assert entered.wait(2)
    final=threading.Thread(target=guard.send,args=(1,'final'));final.start()
    release.set();worker.join(2);final.join(2)
    assert not worker.is_alive() and not final.is_alive()
    assert not guard.emit('late')
    assert [x['text'] for x in out.sent]==['working','final']

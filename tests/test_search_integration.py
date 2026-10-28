"""Run only against isolated temporary storage; never imports production state."""
import os,tempfile,unittest,json
from contextlib import closing
from types import SimpleNamespace
from unittest.mock import patch
TMP=tempfile.TemporaryDirectory(prefix='lectorium-search-tests-')
os.environ['DATA_DIR']=TMP.name+'/data'
os.environ['UPLOAD_DIR']=TMP.name+'/uploads'
os.environ['STORAGE_KEY_FILE']=TMP.name+'/key'
import app.main as m

class IntegrationTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  with closing(m.db()) as c:
   for uid in ('alice','bob'):
    c.execute('INSERT INTO users(id,username,password_hash) VALUES(?,?,?)',(uid,uid,'unused'))
   for lid,uid,fid in [('l1','alice','f1'),('l2','alice','f2'),('private','bob',None)]:
    if fid:c.execute('INSERT INTO folders(id,owner_id,name) VALUES(?,?,?)',(fid,uid,m.encrypt_text(fid)))
    c.execute("INSERT INTO lectures(id,title,source,status,owner_id,folder_id,speech_language,summary,outline,keywords) VALUES(?,?,?,'ready',?,?,'ru',?,?,?)",(lid,m.encrypt_text(lid),m.encrypt_text('fixture'),uid,fid,m.encrypt_text('Пространство и время'),m.encrypt_text('[]'),m.encrypt_text('[]')))
    c.execute('INSERT INTO segments(lecture_id,start,end,text) VALUES(?,120,160,?)',(lid,m.encrypt_text('Философия Канта: пространство и время определяют восприятие.')))
    rows=c.execute('SELECT * FROM segments WHERE lecture_id=? ORDER BY start,id',(lid,)).fetchall()
    digest=m.transcript_source_digest(rows)
    for lang,text in [('en','Space and time shape perception.'),('zh','空间和时间塑造知觉。'),('de','Raum und Zeit bestimmen die Wahrnehmung.'),('es','El espacio y el tiempo determinan la percepción.'),('it','Lo spazio e il tempo determinano la percezione.')]:
     c.execute('INSERT INTO translated_segment_versions(lecture_id,target_language,source_digest,segment_index,text) VALUES(?,?,?,0,?)',(lid,lang,digest,m.encrypt_text(text)))
   c.execute('INSERT INTO translated_segment_versions(lecture_id,target_language,source_digest,segment_index,text) VALUES(?,?,?,?,?)',('l1','en','stale',0,m.encrypt_text('staleprivateword')))
   c.execute('INSERT INTO translated_segments(lecture_id,target_language,segment_index,text) VALUES(?,?,?,?)',('l1','en',0,m.encrypt_text('Space and time shape perception. currenttranslation')))
   c.commit()
  cls.req=SimpleNamespace(state=SimpleNamespace(user_id='alice'))
 def search(self,q,**kw):
  with patch.object(m,'encode_texts',side_effect=RuntimeError('offline')):
   return m.search_materials(self.req,q,**kw)
 def test_languages_spelling_transliteration_and_layout(self):
  for q in ['пространство','space','空间','Raum','espacio','spazio','spcae','currenttranslation','филосфия','filosofiya','abkjcjabz']:
   with self.subTest(q=q):
    rows=self.search(q)
    self.assertTrue(rows)
    self.assertNotIn('private',{r['lecture_id'] for r in rows})
 def test_scope_and_stale_translation(self):
  self.assertEqual({r['lecture_id'] for r in self.search('space',folder_id='f2')},{'l2'})
  self.assertEqual({r['lecture_id'] for r in self.search('space',lecture_id='l1')},{'l1'})
  self.assertEqual(self.search('staleprivateword'),[])
  with self.assertRaises(m.HTTPException):self.search('space',lecture_id='private')
 def test_nonsense_and_limits(self):
  self.assertEqual(self.search('zqxvbnm12345'),[])
  with self.assertRaises(m.HTTPException):self.search('x'*1001)
 def test_assistant_empty_and_extracts(self):
  with patch.object(m,'encode_texts',side_effect=RuntimeError('offline')),patch.object(m.Path,'is_file',return_value=False):
   result=m.assistant(m.AssistantMessage(question='Что такое пространство?',lecture_id='l1'),self.req)
   self.assertEqual(result['mode'],'extracts')
   self.assertTrue(result['sources'])
   self.assertEqual({r['lecture_id'] for r in result['sources']},{'l1'})
   self.assertEqual(m.assistant(m.AssistantMessage(question='zqxvbnm12345'),self.req)['mode'],'no_evidence')
 def test_model_citations_and_busy_fallback(self):
  with patch.object(m,'encode_texts',side_effect=RuntimeError('offline')),patch.object(m.Path,'is_file',return_value=True):
   with patch('app.content.model_response',return_value='Пространство и время определяют восприятие [1].'):
    result=m.assistant(m.AssistantMessage(question='пространство',lecture_id='l1'),self.req)
    self.assertEqual(result['mode'],'generated')
   with patch('app.content.model_response',return_value='Пространство и время определяют восприятие.'):
    self.assertEqual(m.assistant(m.AssistantMessage(question='пространство'),self.req)['mode'],'generated')
   with patch('app.content.model_response',return_value='Unicorns live on Jupiter 9999'):
    self.assertEqual(m.assistant(m.AssistantMessage(question='пространство'),self.req)['mode'],'extracts')
   with patch('app.content.model_response',return_value='Invented citation [99]'):
    self.assertEqual(m.assistant(m.AssistantMessage(question='пространство'),self.req)['mode'],'extracts')
   m._subtitle_model_lock.acquire()
   try:
    with patch('app.content.model_response') as model:
     self.assertEqual(m.assistant(m.AssistantMessage(question='пространство'),self.req)['mode'],'extracts')
     model.assert_not_called()
   finally:m._subtitle_model_lock.release()
 def test_history_and_nonexistent_folder(self):
  self.assertEqual(self.search('space',folder_id='missing'),[])
  with patch.object(m,'search_materials',return_value=[]) as retrieve:
   m.assistant(m.AssistantMessage(question='Почему это так?',history=[{'question':'пространство и время','answer':'text'}]),self.req)
   self.assertIn('пространство и время',retrieve.call_args.args[1])
  with self.assertRaises(m.HTTPException):m.assistant(m.AssistantMessage(question='пространство',language='fr'),self.req)
 def test_bookmarks_and_watch_progress_are_private_and_bounded(self):
  created=m.create_bookmark('l1',m.BookmarkInput(position=130,note='Повторить аргумент'),self.req)
  self.assertEqual(created['note'],'Повторить аргумент')
  self.assertEqual(m.list_bookmarks(self.req)[0]['position'],130)
  m.update_bookmark(created['id'],m.BookmarkUpdate(note='Важный вывод'),self.req)
  self.assertEqual(m.list_bookmarks(self.req)[0]['note'],'Важный вывод')
  m.save_watch_progress('l1',m.WatchProgress(position=140),self.req)
  self.assertEqual(m.list_watch_progress(self.req)[0]['position'],140)
  bob=SimpleNamespace(state=SimpleNamespace(user_id='bob'))
  with self.assertRaises(m.HTTPException):m.create_bookmark('l1',m.BookmarkInput(position=10),bob)
  with self.assertRaises(m.HTTPException):m.update_bookmark(created['id'],m.BookmarkUpdate(note='hack'),bob)
  with self.assertRaises(m.HTTPException):m.save_watch_progress('l1',m.WatchProgress(position=float('nan')),self.req)
  m.delete_bookmark(created['id'],self.req)
  self.assertEqual(m.list_bookmarks(self.req),[])
 def test_translation_model_prefers_optional_large_model(self):
  from pathlib import Path
  import tempfile
  with tempfile.TemporaryDirectory() as directory:
   base=Path(directory)/'base.gguf';large=Path(directory)/'translation.gguf';base.touch()
   with patch.dict(os.environ,{'SUMMARY_MODEL_FILE':str(base),'TRANSLATION_MODEL_FILE':str(large)}):
    self.assertEqual(m.translation_model_file(),base)
    large.touch()
    self.assertEqual(m.translation_model_file(),large)
 def test_unauthorized_endpoint(self):
  # ASGI request without a session must be rejected before retrieval.
  import asyncio
  async def run():
   sent=[]
   async def receive():return {'type':'http.request','body':b'','more_body':False}
   async def send(msg):sent.append(msg)
   await m.app({'type':'http','asgi':{'version':'3.0'},'http_version':'1.1','method':'POST','scheme':'http','path':'/api/assistant','raw_path':b'/api/assistant','query_string':b'','headers':[],'server':('test',80),'client':('test',1)},receive,send)
   self.assertEqual(sent[0]['status'],401)
  asyncio.run(run())

if __name__=='__main__':unittest.main(verbosity=2)

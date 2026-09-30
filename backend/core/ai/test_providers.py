import json
import httpx
from django.test import SimpleTestCase
from .providers import invoke,ProviderFailure
from .contracts import validate_result

def result():
    return {'question_id':'Q1','question_version':1,'status':'needs_information','plain_explanation':'Faltan datos confirmados','suggested_fields':[],'missing_information':['Responsable'],'follow_up_questions':['¿Quién confirma?'],'evidence_required':[],'citations':[],'conflicts':[],'support_level':'insufficient','requires_human_review':True}
class ProviderTests(SimpleTestCase):
    def test_openai_request_and_contract(self):
        def respond(request):
            body=json.loads(request.content)
            self.assertFalse(body['store']);self.assertNotIn('tools',body)
            self.assertTrue(body['text']['format']['strict'])
            self.assertEqual(str(request.url),'https://api.openai.com/v1/responses')
            return httpx.Response(200,json={'status':'completed','output':[{'type':'message','content':[{'type':'output_text','text':json.dumps(result())}]}],'usage':{'input_tokens':10,'output_tokens':30}})
        data=invoke('openai','synthetic-key','synthetic-model',{},transport=httpx.MockTransport(respond))
        self.assertEqual(validate_result(data['result'],'Q1',1,{}).status,'needs_information')
    def test_deepseek_and_incomplete_response(self):
        def respond(request):
            body=json.loads(request.content)
            self.assertEqual(body['response_format'],{'type':'json_object'})
            self.assertEqual(body['thinking'],{'type':'disabled'})
            return httpx.Response(200,json={'choices':[{'finish_reason':'length','message':{'content':'{}'}}],'usage':{'prompt_tokens':5,'completion_tokens':10}})
        with self.assertRaises(ProviderFailure) as failure:invoke('deepseek','synthetic','synthetic',{},transport=httpx.MockTransport(respond))
        self.assertEqual(failure.exception.code,'incomplete')
    def test_unknown_fields_wrong_question_and_invented_citations_are_rejected(self):
        for data in [{**result(),'extra':'no'},{**result(),'question_id':'foreign'},{**result(),'requires_human_review':False},{**result(),'citations':[{'fragment_id':1,'locator':'Invented','quote':'Invented','document_sha256':'a'*64}]}]:
            with self.assertRaises(ValueError):validate_result(data,'Q1',1,{})
    def test_rate_limits_redirects_and_missing_usage_fail_closed(self):
        for status,expected in [(429,'rate_limited'),(503,'temporarily_unavailable'),(302,'provider_rejected')]:
            with self.assertRaises(ProviderFailure) as failure:invoke('openai','synthetic','synthetic',{},transport=httpx.MockTransport(lambda request:httpx.Response(status)))
            self.assertEqual(failure.exception.code,expected)

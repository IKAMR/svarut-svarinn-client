"""All keys, account identifiers and documents here are synthetic and ephemeral."""
from __future__ import annotations

import base64
from contextlib import contextmanager
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from email.parser import BytesParser
from email import policy
import io
import json
from pathlib import Path
import sqlite3
import tempfile
import time
import unittest
from unittest.mock import Mock, MagicMock, patch
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs
from uuid import uuid4

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding, ec
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import NameOID

from svarut_svarinn_client.core.auth import SessionSecrets, MaskinportenClient, make_assertion
from svarut_svarinn_client.core.config import Setup, SvarUtSetup, ConfigStore
from svarut_svarinn_client.core.ks_api import SendDraft, TestOperations, prepare_send, multipart, MAX_PDF_BYTES
from svarut_svarinn_client.core.network import (ApiError, HttpsTransport, NoRedirect, validate_target, http_error,
    TEST_API_BASE, TEST_MASKINPORTEN_BASE, MAX_RESPONSE_BYTES)
from svarut_svarinn_client.core.outbox import OutboxStore
from svarut_svarinn_client.core.paths import AppPaths, StorageError
from svarut_svarinn_client.core.activity import ActivityLog


class FakeTransport:
    def __init__(self, responses=()):
        self.responses = list(responses)
        self.calls = []

    def request(self, method, url, *, headers=None, body=None):
        validate_target(method, url)
        self.calls.append((method, url, headers or {}, body))
        if not self.responses:
            raise AssertionError('Unexpected transport call')
        response = self.responses.pop(0)
        if isinstance(response, BaseException):
            raise response
        return response


class ApiCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.paths = AppPaths(self.root)
        self.paths.prepare()
        self.config = Setup()
        self.config.svarut.api_base_url = self.config.svarinn.api_base_url = TEST_API_BASE
        self.config.svarut.account_id = str(uuid4())
        self.config.svarut.integration_id = str(uuid4())
        self.config.svarut.maskinporten_client_id = str(uuid4())
        self.config.svarut.maskinporten_base_url = TEST_MASKINPORTEN_BASE
        self.config.svarinn.service_username = 'synthetic-service'
        self.secrets = SessionSecrets('synthetic-integration-secret', 'synthetic-key-secret', 'synthetic-service-secret')
        self.transport = FakeTransport()
        self.auth = Mock()
        self.auth.token.return_value = 'synthetic-access-token'
        self.log = ActivityLog(self.paths.activity)
        self.ops = TestOperations(self.paths, transport=self.transport, auth=self.auth, activity=self.log)
        self.pdf = self.root / 'synthetic.pdf'
        self.pdf.write_bytes(b'%PDF-1.7\nsynthetic-test-only\n%%EOF\n')
        self.draft = SendDraft('123456789', 'Synthetic Recipient', 'Synthetic test', str(self.pdf), test_data_confirmed=True)


class ConfigurationUpgradeTests(ApiCase):
    def old_dict(self):
        value = self.config.to_dict()
        value['schema_version'] = 1
        for name in ['maskinporten_base_url', 'maskinporten_key_id', 'signing_certificate_file']:
            value['svarut'].pop(name)
        return value

    def test_old_setup_is_read_without_modifying_file(self):
        value = self.old_dict()
        self.paths.setup.write_text(json.dumps(value))
        before = self.paths.setup.read_bytes()
        store = ConfigStore(self.paths.setup)
        current = store.load_or_create()
        self.assertEqual(current.schema_version, 2)
        self.assertEqual(current.svarinn.service_username, value['svarinn']['service_username'])
        self.assertEqual(self.paths.setup.read_bytes(), before)
        store.save(current)
        self.assertEqual(json.loads(self.paths.setup.read_text())['schema_version'], 2)

    def test_old_setup_unknown_secret_is_not_migrated(self):
        value = self.old_dict()
        value['svarut']['password'] = 'synthetic-forbidden'
        with self.assertRaises(StorageError):
            Setup.from_dict(value)

    def test_secret_representation_does_not_disclose_values(self):
        for value in vars(self.secrets).values():
            self.assertNotIn(value, repr(self.secrets))


class TransportTests(unittest.TestCase):
    def test_only_explicit_test_actions_are_permitted(self):
        account = str(uuid4())
        for method, url in [('GET',TEST_API_BASE+'/svarinn/v2/forsendelser'),
                            ('POST',TEST_API_BASE+f'/v3/kontoer/{account}/forsendelser/organisasjon'),
                            ('POST',TEST_API_BASE+f'/v3/kontoer/{account}/forsendelser/status/sok'),
                            ('POST',TEST_MASKINPORTEN_BASE+'token')]:
            validate_target(method,url)

    def test_production_redirect_and_credential_urls_blocked_before_io(self):
        transport = HttpsTransport()
        transport._opener = Mock()
        for url in ['https://svarut.ks.no/api/svarinn/v2/forsendelser',
                    'https://test.svarut.ks.no.evil.invalid/api/svarinn/v2/forsendelser',
                    'https://user:pass@test.svarut.ks.no/api/svarinn/v2/forsendelser',
                    'https://test.svarut.ks.no:443/api/svarinn/v2/forsendelser',
                    TEST_API_BASE+'/svarinn/v2/forsendelser?token=secret',
                    'http://test.svarut.ks.no/api/svarinn/v2/forsendelser',
                    TEST_API_BASE+'/svarinn/v2/forsendelser/'+str(uuid4()),
                    TEST_MASKINPORTEN_BASE+'../token']:
            with self.subTest(url=url), self.assertRaises(ApiError):
                transport.request('GET',url)
        transport._opener.open.assert_not_called()

    def test_patch_acknowledgement_is_blocked(self):
        with self.assertRaises(ApiError):
            validate_target('PATCH',TEST_API_BASE+'/svarinn/v2/forsendelser/'+str(uuid4())+'/status')

    def test_error_messages_only_include_allowlisted_diagnostics(self):
        error_id = str(uuid4())
        secret = 'synthetic-SENSITIVE-token'
        error = http_error(403,json.dumps({'errorCode':'FIKS-0001','errorId':error_id,
                      'message':secret, 'errorDetails':{'password':secret},'error':secret}).encode())
        self.assertIn('403',str(error));self.assertIn(error_id,str(error));self.assertIn('FIKS-0001',str(error))
        self.assertNotIn(secret,str(error))
        self.assertEqual(error.status,403)

    def test_error_id_cannot_inject_arbitrary_text(self):
        error=http_error(400,b'{"errorId":"not-an-id-private","errorCode":"SECRET","error":"invalid_grant"}')
        self.assertNotIn('not-an-id-private',str(error));self.assertNotIn('SECRET',str(error))
        self.assertIn('invalid_grant',str(error))

    def test_invalid_error_body_does_not_disclose_raw_text(self):
        for raw in [b'secret',b'["secret"]',b'{"error":{"secret":1}}']:
            self.assertNotIn('secret',str(http_error(500,raw)))

    def test_redirect_handler_does_not_follow_any_location(self):
        self.assertIsNone(NoRedirect().redirect_request(None,None,302,'',{},'https://svarut.ks.no/api'))

    def test_transport_converts_http_error_and_does_not_retry(self):
        transport=HttpsTransport();transport._opener=Mock()
        transport._opener.open.side_effect=HTTPError(TEST_API_BASE,401,'secret',{},io.BytesIO(b'raw-secret'))
        with self.assertRaises(ApiError) as result:
            transport.request('GET',TEST_API_BASE+'/svarinn/v2/forsendelser')
        self.assertEqual(result.exception.status,401)
        self.assertNotIn('secret',str(result.exception))
        self.assertEqual(transport._opener.open.call_count,1)

    def test_network_exception_is_sanitized(self):
        transport=HttpsTransport();transport._opener=Mock()
        transport._opener.open.side_effect=URLError('synthetic-private-proxy-token')
        with self.assertRaises(ApiError) as result:
            transport.request('GET',TEST_API_BASE+'/svarinn/v2/forsendelser')
        self.assertNotIn('private',str(result.exception))

    def test_response_limit(self):
        with self.assertRaises(ApiError):
            HttpsTransport._read(io.BytesIO(b' '*(MAX_RESPONSE_BYTES+1)))

    def test_success_path_parses_json_and_checks_tls_context(self):
        transport=HttpsTransport();transport._opener=Mock()
        url=TEST_API_BASE+'/svarinn/v2/forsendelser'
        response=Mock();response.geturl.return_value=url;response.status=200
        response.read.side_effect=[b'[]',b'']
        transport._opener.open.return_value=MagicMock()
        transport._opener.open.return_value.__enter__.return_value=response
        self.assertEqual(transport.request('GET',url),[])
        self.assertEqual(transport._opener.open.call_count,1)
        self.assertGreater(transport._opener.open.call_args.kwargs['timeout'],0)

    def test_duplicate_json_key_is_rejected(self):
        from svarut_svarinn_client.core.network import decode_json
        with self.assertRaises(ApiError):
            decode_json(b'{"id":1,"id":2}')


class MaskinportenTests(ApiCase):
    @classmethod
    def setUpClass(cls):
        cls.key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
        name=x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,'Synthetic Test Certificate')])
        now=datetime.now(timezone.utc)
        cls.cert=(x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(cls.key.public_key())
                  .serial_number(x509.random_serial_number()).not_valid_before(now-timedelta(days=1))
                  .not_valid_after(now+timedelta(days=1)).sign(cls.key,hashes.SHA256()))

    def setUp(self):
        super().setUp()
        self.key_file=self.root/'synthetic-key.pem'
        self.key_file.write_bytes(self.key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,
                                                       serialization.NoEncryption()))
        self.config.svarut.signing_key_file=str(self.key_file)
        self.config.svarut.maskinporten_key_id='synthetic-key-id'

    @staticmethod
    def decode(part):
        return json.loads(base64.urlsafe_b64decode(part+'='*(-len(part)%4)))

    def test_kid_assertion_signature_claims_and_unique_jti(self):
        a=make_assertion(self.config.svarut,'',now=1234567890)
        b=make_assertion(self.config.svarut,'',now=1234567890)
        header,claims,signature=a.split('.')
        self.assertEqual(self.decode(header),{'alg':'RS256','kid':'synthetic-key-id'})
        c=self.decode(claims)
        self.assertEqual(c['aud'],TEST_MASKINPORTEN_BASE);self.assertEqual(c['scope'],'ks:fiks')
        self.assertEqual(c['exp']-c['iat'],120)
        self.assertNotEqual(c['jti'],self.decode(b.split('.')[1])['jti'])
        self.key.public_key().verify(base64.urlsafe_b64decode(signature+'='*(-len(signature)%4)),
                   (header+'.'+claims).encode(),padding.PKCS1v15(),hashes.SHA256())

    def test_p12_x5c_instead_of_kid(self):
        path=self.root/'synthetic.p12'
        path.write_bytes(pkcs12.serialize_key_and_certificates(b'test',self.key,self.cert,None,
                         serialization.BestAvailableEncryption(b'synthetic-p12-password')))
        self.config.svarut.signing_key_file=str(path);self.config.svarut.maskinporten_key_id=''
        token=make_assertion(self.config.svarut,'synthetic-p12-password')
        header=self.decode(token.split('.')[0])
        self.assertNotIn('kid',header)
        self.assertEqual(base64.b64decode(header['x5c'][0]),self.cert.public_bytes(serialization.Encoding.DER))

    def test_separate_pem_certificate(self):
        cert_file=self.root/'synthetic-cert.pem';cert_file.write_bytes(self.cert.public_bytes(serialization.Encoding.PEM))
        self.config.svarut.signing_certificate_file=str(cert_file);self.config.svarut.maskinporten_key_id=''
        header=self.decode(make_assertion(self.config.svarut,'').split('.')[0])
        self.assertIn('x5c',header)

    def test_wrong_key_password_is_safe(self):
        self.key_file.write_bytes(self.key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,
                                 serialization.BestAvailableEncryption(b'correct-synthetic-password')))
        with self.assertRaises(ApiError) as result:
            make_assertion(self.config.svarut,'wrong-synthetic-password')
        self.assertNotIn('wrong-synthetic-password',str(result.exception))
        self.assertNotIn(str(self.key_file),str(result.exception))

    def test_no_kid_or_certificate_is_rejected(self):
        self.config.svarut.maskinporten_key_id=''
        with self.assertRaises(ApiError):
            make_assertion(self.config.svarut,'')

    def test_non_rsa_key_rejected(self):
        other=ec.generate_private_key(ec.SECP256R1())
        self.key_file.write_bytes(other.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()))
        with self.assertRaises(ApiError):
            make_assertion(self.config.svarut,'')

    def test_production_issuer_blocked_before_key_read(self):
        self.config.svarut.maskinporten_base_url='https://maskinporten.no/'
        with patch('svarut_svarinn_client.core.auth._local_file') as read:
            with self.assertRaises(ApiError):
                make_assertion(self.config.svarut,'')
            read.assert_not_called()

    def test_jwk_private_rsa_signs(self):
        numbers=self.key.private_numbers()
        def encoded(n):
            return base64.urlsafe_b64encode(n.to_bytes((n.bit_length()+7)//8,'big')).rstrip(b'=').decode()
        value={'kty':'RSA','n':encoded(numbers.public_numbers.n),'e':encoded(numbers.public_numbers.e)}
        for name,number in [('d',numbers.d),('p',numbers.p),('q',numbers.q),('dp',numbers.dmp1),('dq',numbers.dmq1),('qi',numbers.iqmp)]:
            value[name]=encoded(number)
        path=self.root/'synthetic-key.jwk';path.write_text(json.dumps(value))
        self.config.svarut.signing_key_file=str(path)
        header=self.decode(make_assertion(self.config.svarut,'').split('.')[0])
        self.assertEqual(header['kid'],'synthetic-key-id')

    def test_token_request_form_cache_and_clear(self):
        transport=FakeTransport([{'access_token':'synthetic-token','expires_in':120,'token_type':'Bearer'},
                                 {'access_token':'second-synthetic-token','expires_in':120,'token_type':'Bearer'}])
        auth=MaskinportenClient(transport);secrets=SessionSecrets()
        self.assertEqual(auth.token(self.config.svarut,secrets),'synthetic-token')
        self.assertEqual(auth.token(self.config.svarut,secrets),'synthetic-token')
        self.assertEqual(len(transport.calls),1)
        body=parse_qs(transport.calls[0][3].decode())
        self.assertEqual(body['grant_type'],['urn:ietf:params:oauth:grant-type:jwt-bearer'])
        self.assertIn('assertion',body)
        auth.clear()
        self.assertEqual(auth.token(self.config.svarut,secrets),'second-synthetic-token')

    def test_changed_setup_invalidates_token_cache(self):
        transport=FakeTransport([{'access_token':v,'expires_in':120,'token_type':'Bearer'} for v in ['first','second']])
        auth=MaskinportenClient(transport)
        auth.token(self.config.svarut,SessionSecrets())
        self.config.svarut.maskinporten_client_id=str(uuid4())
        self.assertEqual(auth.token(self.config.svarut,SessionSecrets()),'second')
        self.assertEqual(len(transport.calls),2)

    def test_malformed_token_response_rejected(self):
        for response in [{},[],{'access_token':'has\nnewline','expires_in':100,'token_type':'Bearer'},
                         {'access_token':'synthetic','expires_in':True,'token_type':'Bearer'}]:
            with self.subTest(response_type=type(response).__name__),self.assertRaises(ApiError):
                MaskinportenClient(FakeTransport([response])).token(self.config.svarut,SessionSecrets())


class SvarInnTests(ApiCase):
    def test_empty_list_authenticates_without_maskinporten_or_keys(self):
        self.transport.responses=[[]]
        self.assertEqual(self.ops.list_incoming(self.config,self.secrets),[])
        self.auth.token.assert_not_called()
        method,url,headers,body=self.transport.calls[0]
        self.assertEqual(method,'GET');self.assertEqual(url,TEST_API_BASE+'/svarinn/v2/forsendelser')
        self.assertEqual(base64.b64decode(headers['Authorization'].split()[1]).decode(),
                          self.config.svarinn.service_username+':'+self.secrets.svarinn_password)
        self.assertIsNone(body)

    def test_list_tolerates_new_fields_and_does_not_follow_download_links(self):
        identifier=str(uuid4())
        self.transport.responses=[[{'id':identifier,'tittel':'Synthetic title','dato':'2026-01-01T10:00:00Z',
                                   'filer':[{'mimeType':'application/pdf'}], 'newField':True,
                                   'nedlastingslenke':'https://evil.invalid/secret'}]]
        result=self.ops.list_incoming(self.config,self.secrets)
        self.assertEqual(result[0]['id'],identifier);self.assertEqual(result[0]['files'],1)
        self.assertEqual(len(self.transport.calls),1)
        self.assertNotIn('evil',str(result))

    def test_no_service_password_means_no_network(self):
        with self.assertRaises(ApiError):
            self.ops.list_incoming(self.config,SessionSecrets())
        self.assertEqual(self.transport.calls,[])

    def test_invalid_list_is_not_misreported_as_empty(self):
        for response in [{},None,[{}], [{'id':'not-an-id','filer':[]}]]:
            self.transport.responses=[response]
            with self.subTest(response=response),self.assertRaises(ApiError):
                self.ops.list_incoming(self.config,self.secrets)

    def test_list_never_persists_incoming_titles_or_credentials(self):
        title='synthetic-title-not-for-logs'
        self.transport.responses=[[{'id':str(uuid4()),'tittel':title,'filer':[]}]]
        self.ops.list_incoming(self.config,self.secrets)
        raw=self.paths.activity.read_text()
        for value in [title,*vars(self.secrets).values()]:
            self.assertNotIn(value,raw)
        self.assertFalse((self.root/'inbox').exists())


class SendingTests(ApiCase):
    def test_multipart_metadata_is_first_and_filename_matches_pdf_part(self):
        prepared=prepare_send(self.draft,account_id=self.config.svarut.account_id,api_base=TEST_API_BASE)
        content_type,body=multipart(prepared)
        mail=BytesParser(policy=policy.default).parsebytes(('Content-Type: '+content_type+'\r\n\r\n').encode()+body)
        parts=list(mail.iter_parts())
        self.assertEqual(len(parts),2)
        self.assertEqual(parts[0].get_param('name',header='Content-Disposition'),'forsendelse')
        metadata=json.loads(parts[0].get_payload(decode=True))
        self.assertEqual(metadata['mottaker'],{'navn':'Synthetic Recipient','digitalId':'123456789'})
        self.assertTrue(metadata['kunDigitalLevering'])
        self.assertEqual(metadata['dokumenter'][0]['filnavn'],parts[1].get_filename())
        self.assertEqual(parts[1].get_payload(decode=True),self.pdf.read_bytes())

    def test_unicode_filename_and_title_survive_multipart(self):
        filename=self.root/'synthetic-æøå.pdf';filename.write_bytes(self.pdf.read_bytes())
        prepared=prepare_send(replace(self.draft,pdf_file=str(filename),title='Test æøå'),account_id='synthetic',api_base=TEST_API_BASE)
        content_type,body=multipart(prepared)
        self.assertIn(filename.name.encode('utf-8'),body)
        self.assertIn('Test æøå'.encode(),body)

    def test_send_records_acceptance_and_status_contract(self):
        identifier=str(uuid4())
        self.transport.responses=[{'id':identifier}, {'statuser':[{'id':identifier,'status':'KLAR_FOR_MOTTAK','sisteStatusEndring':'2026-01-01T10:00:00Z'}]}]
        result=self.ops.send(self.config,self.secrets,self.draft)
        self.assertEqual(result['id'],identifier)
        row=self.ops.outbox.recent()[0];self.assertEqual(row['state'],'ACCEPTED');self.assertEqual(row['remote_id'],identifier)
        status=self.ops.status(self.config,self.secrets,identifier)
        self.assertEqual(status['status'],'KLAR_FOR_MOTTAK')
        self.assertEqual(json.loads(self.transport.calls[1][3]),{'id':[identifier]})
        self.assertTrue(self.transport.calls[1][1].endswith('/forsendelser/status/sok'))
        self.assertEqual(self.ops.outbox.recent()[0]['ks_status'],'KLAR_FOR_MOTTAK')
        self.assertEqual(self.transport.calls[0][2]['IntegrasjonId'],self.config.svarut.integration_id)

    def test_journal_exists_before_remote_send(self):
        identifier=str(uuid4())
        def inspect_request(*args,**kwargs):
            self.assertEqual(self.ops.outbox.recent()[0]['state'],'SENDING')
            return {'id':identifier}
        with patch.object(self.transport,'request',side_effect=inspect_request):
            self.ops.send(self.config,self.secrets,self.draft)

    def test_test_confirmation_is_required_in_core(self):
        with self.assertRaises(ApiError):
            self.ops.send(self.config,self.secrets,replace(self.draft,test_data_confirmed=False))
        self.assertEqual(self.transport.calls,[])

    def test_invalid_document_prevents_network(self):
        self.pdf.write_bytes(b'not-pdf')
        with self.assertRaises(ApiError):
            self.ops.send(self.config,self.secrets,self.draft)
        self.assertEqual(self.transport.calls,[]);self.auth.token.assert_not_called()

    def test_local_file_limit_prevents_network(self):
        with self.pdf.open('wb') as f:
            f.write(b'%PDF-1.7\n');f.truncate(MAX_PDF_BYTES+1)
        with self.assertRaises(ApiError):
            self.ops.send(self.config,self.secrets,self.draft)
        self.assertEqual(self.transport.calls,[])

    def test_missing_integration_password_does_not_send(self):
        with self.assertRaises(ApiError):
            self.ops.send(self.config,SessionSecrets(),self.draft)
        self.assertEqual(self.transport.calls,[])

    def test_timeout_is_unknown_and_no_auto_retry(self):
        self.transport.responses=[ApiError('Synthetic timeout')]
        with self.assertRaises(ApiError) as result:
            self.ops.send(self.config,self.secrets,self.draft)
        self.assertIn('UKJENT',str(result.exception))
        self.assertEqual(len(self.transport.calls),1)
        self.assertEqual(self.ops.outbox.recent()[0]['state'],'UNKNOWN')
        with self.assertRaises(ApiError):
            self.ops.send(self.config,self.secrets,self.draft)
        self.assertEqual(len(self.transport.calls),1)

    def test_malformed_success_and_5xx_are_unknown(self):
        for i,response in enumerate([{}, {'id':'bad'}, ApiError('Server error',status=500)]):
            self.transport.responses=[response]
            with self.assertRaises(ApiError):
                self.ops.send(self.config,self.secrets,replace(self.draft,title='Synthetic '+str(i)))
        self.assertTrue(all(row['state']=='UNKNOWN' for row in self.ops.outbox.recent()))

    def test_4xx_rejection_allows_new_explicit_attempt(self):
        self.transport.responses=[ApiError('Forbidden',status=403),{'id':str(uuid4())}]
        with self.assertRaises(ApiError):
            self.ops.send(self.config,self.secrets,self.draft)
        self.assertEqual(self.ops.outbox.recent()[0]['state'],'REJECTED')
        self.ops.send(self.config,self.secrets,self.draft)
        self.assertEqual(len(self.transport.calls),2)

    def test_accepted_duplicate_is_blocked_including_after_restart(self):
        self.transport.responses=[{'id':str(uuid4())}]
        self.ops.send(self.config,self.secrets,self.draft)
        restarted=TestOperations(self.paths,transport=self.transport,auth=self.auth)
        with self.assertRaises(ApiError):
            restarted.send(self.config,self.secrets,self.draft)
        self.assertEqual(len(self.transport.calls),1)

    def test_storage_failure_before_post_prevents_sending(self):
        with patch.object(self.ops.outbox,'begin',side_effect=StorageError('synthetic')):
            with self.assertRaises(StorageError):
                self.ops.send(self.config,self.secrets,self.draft)
        self.assertEqual(self.transport.calls,[])

    def test_storage_failure_after_post_preserves_remote_id_in_error(self):
        identifier=str(uuid4());self.transport.responses=[{'id':identifier}]
        with patch.object(self.ops.outbox,'outcome',side_effect=StorageError('synthetic')):
            with self.assertRaises(ApiError) as result:
                self.ops.send(self.config,self.secrets,self.draft)
        self.assertIn(identifier,str(result.exception));self.assertIn('IKKE',str(result.exception))
        self.assertEqual(self.ops.outbox.recent()[0]['state'],'SENDING')

    def test_restart_marks_interrupted_sending_unknown(self):
        prepared=prepare_send(self.draft,account_id=self.config.svarut.account_id,api_base=TEST_API_BASE)
        self.ops.outbox.begin(reference=prepared.reference,fingerprint=prepared.fingerprint,
               account_id=self.config.svarut.account_id,api_base=TEST_API_BASE,recipient='123456789',
               recipient_name='Synthetic Recipient',title='Synthetic test',filename=prepared.filename,sha256=prepared.sha256)
        restarted=TestOperations(self.paths,transport=self.transport,auth=self.auth)
        self.assertEqual(restarted.outbox.recent()[0]['state'],'UNKNOWN')
        self.assertEqual(self.transport.calls,[])

    def test_diagnostic_log_failure_does_not_mask_accepted_send(self):
        identifier=str(uuid4());self.transport.responses=[{'id':identifier}]
        with patch.object(self.log,'append',side_effect=StorageError('synthetic')):
            self.assertEqual(self.ops.send(self.config,self.secrets,self.draft)['id'],identifier)

    def test_password_and_document_contents_never_persist_in_journal_or_log(self):
        self.transport.responses=[{'id':str(uuid4())}]
        self.ops.send(self.config,self.secrets,self.draft)
        for path in self.root.rglob('*'):
            if path.is_file() and path != self.pdf:
                raw=path.read_bytes()
                for value in [*vars(self.secrets).values(),'synthetic-access-token','synthetic-test-only']:
                    self.assertNotIn(value.encode(),raw)

    def test_status_unknown_enum_is_preserved(self):
        identifier=str(uuid4());self.transport.responses=[{'statuser':[{'id':identifier,'status':'FUTURE_STATUS','sisteStatusEndring':'synthetic-time'}]}]
        self.assertEqual(self.ops.status(self.config,self.secrets,identifier)['status'],'FUTURE_STATUS')

    def test_empty_status_is_not_claimed_as_delivery(self):
        self.transport.responses=[{'statuser':[]}]
        self.assertIsNone(self.ops.status(self.config,self.secrets,str(uuid4())))

    def test_status_for_wrong_id_rejected(self):
        self.transport.responses=[{'statuser':[{'id':str(uuid4()),'status':'LEST','sisteStatusEndring':'synthetic'}]}]
        with self.assertRaises(ApiError):
            self.ops.status(self.config,self.secrets,str(uuid4()))

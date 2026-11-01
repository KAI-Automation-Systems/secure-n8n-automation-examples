import json
import unittest
from unittest.mock import patch

from automation.providers import AnthropicProvider, NoRedirect


class Response:
    def __init__(self, value):
        self.value = value

    def __enter__(self):
        return self

    def __exit__(self, *_):
        pass

    def read(self, size):
        return self.value[:size]


class ProviderTests(unittest.TestCase):
    def provider(self):
        with patch.dict('os.environ', {'ALLOW_EXTERNAL_MODEL': 'true', 'ANTHROPIC_API_KEY': 'test-key',
                                      'ANTHROPIC_MODEL': 'test-model'}):
            return AnthropicProvider()

    def test_explicit_opt_in_required(self):
        with patch.dict('os.environ', {}, clear=True), self.assertRaises(ValueError):
            AnthropicProvider()

    def test_provider_rejects_free_text_and_unknown_features(self):
        p = self.provider()
        for features in [{'body': 'secret'}, {'billing': 'false', 'technical': False, 'urgent': False}]:
            with self.assertRaises(ValueError):
                p.classify(features)

    def test_fixed_host_minimised_body_and_timeout(self):
        p = self.provider()
        response = {'stop_reason': 'end_turn', 'content': [{'type': 'text', 'text': '{"category":"general","priority":"normal"}'}]}
        captured = []
        def opening(request, timeout):
            captured.append((request, timeout))
            return Response(json.dumps(response).encode())
        with patch.object(p.opener, 'open', side_effect=opening):
            self.assertEqual(p.classify({'billing':False, 'technical':False, 'urgent':False})['category'], 'general')
        request, timeout = captured[0]
        self.assertEqual(request.full_url, 'https://api.anthropic.com/v1/messages')
        self.assertEqual(timeout, 8)
        outgoing = json.loads(request.data)
        self.assertEqual(json.loads(outgoing['messages'][0]['content']), {'billing':False, 'technical':False, 'urgent':False})
        self.assertNotIn('tools', outgoing)

    def test_incomplete_tool_or_oversized_response_rejected(self):
        p = self.provider()
        values = [b'x' * 40000,
                  json.dumps({'stop_reason':'max_tokens', 'content':[]}).encode(),
                  json.dumps({'stop_reason':'end_turn', 'content':[{'type':'tool_use'}]}).encode()]
        for value in values:
            with patch.object(p.opener, 'open', return_value=Response(value)), self.assertRaises(ValueError):
                p.classify({'billing':False, 'technical':False, 'urgent':False})

    def test_redirect_handler_never_forwards_request(self):
        self.assertIsNone(NoRedirect().redirect_request(None, None, 302, '', {}, 'https://evil.invalid'))

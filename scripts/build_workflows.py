"""Reproducible, credential-free n8n templates; never auto-activate."""
import json
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def node(name, kind, version, position, parameters):
    return {"id": str(uuid.uuid5(uuid.NAMESPACE_URL, 'kai-demo:' + name)), "name": name,
            "type": "n8n-nodes-base." + kind, "typeVersion": version,
            "position": position, "parameters": parameters}


def build(kind, fields):
    names = ['Authenticated request', 'Allowlisted payload', 'Submit for review', 'Return status']
    code = '''const p = $input.first().json.body;
const fields = FIELDS;
if (!p || typeof p !== 'object' || Array.isArray(p) ||
    Object.keys(p).sort().join(',') !== [...fields].sort().join(',')) {
  throw new Error('Invalid request fields');
}
// Drop request headers, webhook metadata and credentials immediately.
// Authoritative value validation and all state transitions live in the gateway.
return [{json: Object.fromEntries(fields.map(k => [k, p[k]]))}];'''.replace('FIELDS', json.dumps(fields))
    nodes = [
        node(names[0], 'webhook', 2, [0, 0], {
            "httpMethod": "POST", "path": 'kai-demo-' + kind,
            "authentication": "headerAuth", "responseMode": "responseNode", "options": {}}),
        node(names[1], 'code', 2, [260, 0], {"jsCode": code}),
        node(names[2], 'httpRequest', 4.2, [520, 0], {
            "method": "POST", "url": 'http://127.0.0.1:8080/v1/' + kind,
            "authentication": "genericCredentialType", "genericAuthType": "httpHeaderAuth",
            "sendBody": True, "specifyBody": "json", "jsonBody": '={{ JSON.stringify($json) }}',
            "options": {"timeout": 20000, "redirect": {"redirect": {"followRedirects": False}},
                        "response": {"response": {"fullResponse": True, "neverError": True, "responseFormat": "json"}}}}),
        node(names[3], 'respondToWebhook', 1.4, [780, 0], {
            "respondWith": "json", "responseBody": '={{ $json.body }}',
            "options": {"responseCode": '={{ $json.statusCode }}',
                        "responseHeaders": {"entries": [{"name": "Cache-Control", "value": "no-store"}]}}}),
    ]
    result = {"name": 'KAI Demo | ' + kind, "active": False, "nodes": nodes,
              "connections": {names[i]: {"main": [[{"node": names[i+1], "type": "main", "index": 0}]]} for i in range(3)},
              "settings": {"executionOrder": "v1", "saveDataSuccessExecution": "none", "saveDataErrorExecution": "none",
                           "saveManualExecutions": False, "saveExecutionProgress": False, "executionTimeout": 30},
              "pinData": {}, "tags": []}
    directory = ROOT / 'workflows'; directory.mkdir(exist_ok=True)
    (directory / (kind + '.json')).write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    build('intakes', ['event_id', 'subject', 'body'])
    build('invoices', ['event_id', 'supplier_ref', 'invoice_ref', 'currency', 'net', 'tax', 'gross'])

import fs from 'node:fs';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import test from 'node:test';

for (const kind of ['intakes', 'invoices']) {
  const w = JSON.parse(fs.readFileSync(new URL(`../workflows/${kind}.json`, import.meta.url), 'utf8'));
  test(`${kind}: closed credential-free import and connected response path`, () => {
    assert.equal(w.active, false);
    assert.equal(w.nodes[0].parameters.authentication, 'headerAuth');
    assert.equal(w.nodes[2].parameters.genericAuthType, 'httpHeaderAuth');
    assert.equal(w.nodes[2].parameters.url, `http://127.0.0.1:8080/v1/${kind}`);
    assert.equal(w.settings.saveDataErrorExecution, 'none');
    assert.equal(w.settings.saveDataSuccessExecution, 'none');
    assert.equal(w.settings.saveManualExecutions, false);
    assert.deepEqual(w.pinData, {});
    assert.ok(w.nodes.every(n => !n.credentials));
    for (let i = 0; i < 3; i++) assert.equal(w.connections[w.nodes[i].name].main[0][0].node, w.nodes[i+1].name);
  });
  const body = kind === 'intakes' ? {event_id: 'request-demo-001', subject: 'API Fehler', body: 'Synthetic test'} :
    {event_id: 'invoice-demo-001', supplier_ref: 'supplier-demo', invoice_ref: 'invoice-demo-001', currency: 'EUR', net: '100.00', tax: '20.00', gross: '120.00'};
  const execute = input => vm.runInNewContext(`(function(){${w.nodes[1].parameters.jsCode}})()`, {
    $input: {first: () => ({json: input})},
  });
  test(`${kind}: Code node strips credentials and metadata`, () => {
    const output = JSON.parse(JSON.stringify(execute({body, headers: {authorization: 'secret-test-marker'}})));
    assert.deepEqual(output, [{json: body}]);
    assert.ok(!JSON.stringify(output).includes('secret-test-marker'));
  });
  test(`${kind}: Code node rejects hidden fields and nonobjects`, () => {
    assert.throws(() => execute({body: {...body, callback_url: 'http://169.254.169.254'}}));
    assert.throws(() => execute({body: 'bad'}));
    assert.throws(() => execute({body: []}));
  });
}

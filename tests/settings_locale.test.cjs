const {test} = require('node:test');
const assert = require('node:assert/strict');
const {JSDOM} = require('jsdom');
const fs = require('node:fs');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, '../custom_components/claude_assistant/frontend/panel.js'), 'utf8');
function setup(language='en', auth_type='personal_account') {
  const dom = new JSDOM('<body></body>', {runScripts:'outside-only'});
  dom.window.eval(source);
  const calls=[];
  const settings={auth_type,model:'claude-sonnet-5',safety_level:'dangerous_only',system_prompt:'literal <>&',temperature:0.7,max_tokens:2048};
  const connection={sendMessagePromise:async msg => {
    calls.push(msg);
    return msg.type==='claude_assistant/settings' ? {settings} : {stats:{}};
  }};
  const panel=dom.window.document.createElement('claude-assistant-panel');
  dom.window.document.body.append(panel);
  panel.hass={language,connection};
  return {dom,panel,calls,connection};
}
async function ready() { await new Promise(resolve=>setImmediate(resolve)); }
for (const [language,auth,expected] of [['en','personal_account','Personal account'],['en','api_key','API key'],['pl-PL','personal_account','Konto osobiste'],['pl','api_key','Klucz API'],['fr','personal_account','Personal account']]) {
  test(`settings language ${language}, auth ${auth}`,async()=>{
    const {dom,panel}=setup(language,auth); await ready();
    const text=panel.shadowRoot.getElementById('settings-content').textContent;
    assert.ok(text.includes(expected));
    if (language.startsWith('pl')) {
      for (const s of ['Uwierzytelnianie','Parametry generowania','Bezpieczeństwo','Instrukcje dla Claude','Potwierdzaj wszystkie działania']) assert.ok(text.includes(s),s);
      assert.equal(panel.shadowRoot.querySelector('[data-tab="settings"]').textContent,'⚙️ Ustawienia');
    } else {
      for (const s of ['Authentication','Generation parameters','Safety','Instructions for Claude','Changing this requires reconfiguring the integration']) assert.ok(text.includes(s),s);
      assert.ok(!text.includes('Konto osobiste') && !text.includes('Zmiana wymaga'));
    }
    assert.equal(panel.shadowRoot.getElementById('set-prompt').value,'literal <>&');
    dom.window.close();
  });
}
test('ordinary locale changes retain controls, draft, focus and one pending save',async()=>{
  const {dom,panel,calls,connection}=setup(); await ready();
  const shadow=panel.shadowRoot;
  const input=shadow.getElementById('set-prompt');
  shadow.getElementById('tab-settings').classList.add('active');
  input.focus(); input.value='unsaved <draft> & text'; input.setSelectionRange(3,9);
  input.dispatchEvent(new dom.window.Event('input',{bubbles:true}));
  const reads=calls.length;
  panel.hass={language:'pl',connection};
  assert.ok(shadow.getElementById('settings-content').textContent.includes('Uwierzytelnianie'));
  panel.hass={language:'en',connection};
  assert.equal(panel.shadowRoot,shadow);
  assert.equal(shadow.getElementById('set-prompt'),input);
  assert.equal(input.value,'unsaved <draft> & text');
  assert.equal(shadow.activeElement,input);
  assert.equal(input.selectionStart,3); assert.equal(input.selectionEnd,9);
  assert.equal(calls.length,reads);
  await new Promise(resolve=>setTimeout(resolve,1100));
  const writes=calls.filter(x=>x.type==='claude_assistant/update_settings');
  assert.equal(writes.length,1);
  assert.equal(writes[0].system_prompt,'unsaved <draft> & text');
  dom.window.close();
});
test('instances localize independently and control values still reach server',async()=>{
  const en=setup(),pl=setup('pl'); await ready();
  const select=pl.panel.shadowRoot.getElementById('set-safety');
  select.value='none'; select.dispatchEvent(new pl.dom.window.Event('change'));
  await ready();
  assert.equal(pl.calls.at(-1).safety_level,'none');
  assert.ok(en.panel.shadowRoot.getElementById('settings-content').textContent.includes('Authentication'));
  assert.ok(pl.panel.shadowRoot.getElementById('settings-content').textContent.includes('Uwierzytelnianie'));
  en.dom.window.close(); pl.dom.window.close();
});

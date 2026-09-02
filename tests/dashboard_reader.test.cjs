// Run with: node --test tests/dashboard_reader.test.cjs
// Exercise UI state without a browser, server, or AI provider.
const {test}=require('node:test');
const assert=require('node:assert/strict');
const {readFileSync}=require('node:fs');
const {join}=require('node:path');
const vm=require('node:vm');

function setup(){
  const nodes=new Map(), classes=new Set(), listeners={};
  const document={
    body:{classList:{
      toggle(name,on){on?classes.add(name):classes.delete(name)},
      contains(name){return classes.has(name)},
    }},
    getElementById(id){
      if(!nodes.has(id))nodes.set(id,{
        hidden:false, attributes:{}, textContent:'',
        setAttribute(name,value){this.attributes[name]=value},
        focus(){this.focused=true},
      });
      return nodes.get(id);
    },
    addEventListener(name,callback){listeners[name]=callback},
    querySelector(){return document.openDialog?{}:null},
  };
  const context=vm.createContext({
    document, console, location:{hash:''},
    // Leave bootstrap pending so no network or background polling occurs.
    fetch:()=>new Promise(()=>{}), setTimeout(){},
  });
  vm.runInContext(readFileSync(join(__dirname,'../definalyzer/dashboard_assets/app.js'),'utf8'),context);
  return {document, nodes, classes, listeners};
}

test('expand and restore update layout and accessible button state',()=>{
  const {nodes,classes}=setup();
  const button=nodes.get('expand-reader');
  button.onclick();
  assert.equal(classes.has('reader-expanded'),true);
  assert.equal(button.attributes['aria-pressed'],'true');
  assert.equal(button.textContent,'Restore layout');
  button.onclick();
  assert.equal(classes.has('reader-expanded'),false);
  assert.equal(button.attributes['aria-pressed'],'false');
  assert.equal(button.textContent,'Expand page');
});

test('Escape restores layout and returns focus to the toggle',()=>{
  const {nodes,classes,listeners}=setup();
  const button=nodes.get('expand-reader');
  button.onclick();
  listeners.keydown({key:'Escape'});
  assert.equal(classes.has('reader-expanded'),false);
  assert.equal(button.focused,true);
});

test('Escape belongs to an open dialog before the expanded reader',()=>{
  const {document,nodes,classes,listeners}=setup();
  nodes.get('expand-reader').onclick();
  document.openDialog=true;
  listeners.keydown({key:'Escape'});
  assert.equal(classes.has('reader-expanded'),true);
  document.openDialog=false;
  listeners.keydown({key:'Escape'});
  assert.equal(classes.has('reader-expanded'),false);
});

test('an empty reader cannot enter expanded mode',()=>{
  const {document,nodes,classes}=setup();
  document.getElementById('reader').hidden=true;
  nodes.get('expand-reader').onclick();
  assert.equal(classes.has('reader-expanded'),false);
});

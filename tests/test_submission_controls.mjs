import test from 'node:test';
import assert from 'node:assert/strict';
import {runInNewContext} from 'node:vm';
import {readSubmissionCandidates} from '../browser/submission_controls.mjs';

function discover(labels,messages=[],outcomes=false){
 const element=(id,label)=>({id,innerText:label,value:label,children:[],disabled:false,
  matches:()=>false,getClientRects:()=>[{}],getAttribute:()=>null});
 const controls=labels.map((s,i)=>element('button-'+i,s));
 const notices=messages.map((s,i)=>element('message-'+i,s));
 const all=[...controls,...notices];
 const document={body:{},querySelectorAll:selector=>selector.startsWith('#')?all.filter(e=>e.id===selector.slice(1)):
  selector==='body *'?all:controls};
 return JSON.parse(JSON.stringify(runInNewContext('('+readSubmissionCandidates.toString()+')({outcomes:'+outcomes+'})',{
  document,CSS:{escape:s=>s},getComputedStyle:()=>({visibility:'visible'})})));
}

test('submission uses observed English and Chinese labels without requiring a site class',()=>{
 const candidates=discover(['Submit Application','提交申请','Delete account','保存']);
 assert.deepEqual(candidates.map(c=>c.text),['Submit Application','提交申请']);
 assert.equal(candidates[0].selector,'#button-0');
});
test('different observed success wording is offered for independent review',()=>{
 const candidates=discover([],['投递成功','Application submitted','Thank you for applying'],true);
 assert.equal(candidates.length,3);
 assert.ok(candidates.every(c=>c.kind==='success'));
});
test('failure notices cannot be success candidates',()=>{
 assert.equal(discover([],['未提交成功，请重试','Application was not submitted','Submission failed'],true).length,0);
});
test('confirmation control is not itself a successful submission',()=>{
 const candidates=discover(['Confirm submission'],[],true);
 assert.equal(candidates.length,1);
 assert.equal(candidates[0].kind,'confirmation');
});

/** Serialized read-only discovery. Returned controls are candidates, never authorization. */
export function readSubmissionCandidates({outcomes=false}={}) {
 const visible=e=>!!e.getClientRects().length&&getComputedStyle(e).visibility!=='hidden';
 const text=e=>(e.matches('input')?e.value:e.innerText||'').trim();
 const path=e=>{
  if(e.id&&document.querySelectorAll('#'+CSS.escape(e.id)).length===1)return '#'+CSS.escape(e.id);
  const parts=[];
  while(e&&e!==document.body){const peers=[...e.parentElement.children].filter(x=>x.tagName===e.tagName);
   parts.unshift(e.tagName.toLowerCase()+':nth-of-type('+(peers.indexOf(e)+1)+')');e=e.parentElement;}
  return 'body > '+parts.join(' > ');
 };
 const submit=/^(?:预览并提交|提交简历|投递简历|确认提交|确认投递|提交申请|确认申请|立即申请|立即投递|提交|投递|submit(?: application)?|apply(?: now)?|send application|confirm(?: application| submission)?)$/i;
 const controls=[...document.querySelectorAll('button,[role="button"],input[type="submit"]')]
  .filter(e=>visible(e)&&!e.disabled&&e.getAttribute('aria-disabled')!=='true'&&submit.test(text(e).replace(/\s+/g,' ')))
  .map(e=>({selector:path(e),text:text(e),input_value:e.matches('input'),kind:'action'}));
 if(!outcomes)return controls.map((e,i)=>({...e,id:'action-'+(i+1)}));
 const success=/(?:申请成功|投递成功|提交成功|成功提交|已成功提交申请|已收到.{0,20}申请|application (?:has been |was )?(?:successfully )?(?:submitted|received)|thank you for applying|successfully (?:submitted|applied))/i;
 const messages=[...document.querySelectorAll('body *')].filter(e=>visible(e)&&text(e).length<600&&success.test(text(e))&&!/(?:\bnot\b|\bunsuccessful\b|\bfailed\b|未.{0,8}成功|失败)/i.test(text(e))&&
  ![...e.children].some(child=>visible(child)&&success.test(text(child))));
 return [...messages.map(e=>({selector:path(e),text:text(e),kind:'success'})), ...controls.map(c=>({...c,kind:'confirmation'}))]
  .map((e,i)=>({...e,id:'outcome-'+(i+1)}));
}

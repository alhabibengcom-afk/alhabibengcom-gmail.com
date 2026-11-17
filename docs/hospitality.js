(()=>{
const allRooms=Array.from(document.querySelectorAll('.p4entry'));
const selection=Array.from(document.querySelectorAll('[data-room-num]'));
function room(n) {
 if(n<1||n>allRooms.length)return;
 allRooms.forEach((v,i)=>{v.hidden=i!==n-1});
 selection.forEach((b,i)=>b.setAttribute('aria-pressed',String(i===n-1)));
}
selection.forEach(b=>b.addEventListener('click',()=>{room(Number(b.dataset.roomNum));if(matchMedia('(max-width:850px)').matches)document.querySelector('#hotelprofile').scrollIntoView({block:'start',behavior:'instant'})}));
room(7);
const ranges=[[.2,.03,.005,1.2,25,180],[.3,.05,.01,1.5,30,240],[.4,.08,.0175,1.8,35,300]], pop=[1769,272905,536941];
const nb=new Intl.NumberFormat('ar-EG',{maximumFractionDigits:0}), conv=document.getElementById('mconv'), basket=document.getElementById('mbasket'), buttons=Array.from(document.querySelectorAll('[data-sc]'));
let active=1;
function calculate(){
 const s=ranges[active],vis=pop.reduce((v,p,i)=>v+p*s[i],0)*s[3];
 const outs=document.querySelectorAll('[data-result]');
 outs[0].textContent=nb.format(vis);
 outs[1].textContent=nb.format(vis/30);
 if(!conv.value||!basket.value||!conv.validity.valid||!basket.validity.valid){outs[2].textContent='—';document.getElementById('mnote').textContent='أدخل نسبة بين ٠ و١٠٠ ومتوسط إنفاق موجبًا.';return}
 outs[2].textContent=nb.format(vis*(+conv.value)/100*(+basket.value));
 document.getElementById('mnote').textContent='عدد الزيارات المصحوبة بشراء وفق المدخلات الحالية: '+nb.format(vis*(+conv.value)/100)+' شهريًا.';
}
function scenario(n){active=n;conv.value=ranges[n][4];basket.value=ranges[n][5];buttons.forEach((b,i)=>b.setAttribute('aria-pressed',String(i===n)));calculate()}
buttons.forEach(b=>b.addEventListener('click',()=>scenario(Number(b.dataset.sc))));conv.addEventListener('input',calculate);basket.addEventListener('input',calculate);scenario(1);
document.addEventListener('play', event => {
  if (!(event.target instanceof HTMLVideoElement)) return;
  for (const video of document.querySelectorAll('video')) {
    if (video !== event.target && !video.paused) video.pause();
  }
}, true);
})();

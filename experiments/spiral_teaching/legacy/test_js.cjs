const fs=require('fs'),vm=require('vm'),assert=require('assert');
const html=fs.readFileSync(__dirname+'/spiral_wire.html','utf8');
const js=html.match(/<script>([\s\S]*?)<\/script>/)[1];
const core=js.slice(0,js.indexOf("el('pack').addEventListener"));
const context=vm.createContext({document:{getElementById:()=>({})}});
vm.runInContext(core+'\nthis.TEST={packData,unpackData,makeQuestion,fromLines,checkField};',context);
const {packData,unpackData,makeQuestion,fromLines}=context.TEST;
const sample=['01001110','1110','010001110','01110','0100011000111110'];
assert.equal(JSON.stringify([...unpackData(packData(sample)).xs]),JSON.stringify(sample));
assert.equal(unpackData(packData(sample)).terminal,true);
assert.equal(JSON.stringify([...unpackData(packData(sample,false)).xs]),JSON.stringify(sample));
assert.equal(unpackData(packData(sample,false)).terminal,false);
assert.equal('1111111111111111'.length,16);
assert.equal(unpackData(packData(['01001110','1110'])).xs.length,2);
const ex=makeQuestion('neg','001010');assert.equal(ex.a,'110100');
const cases=[['echo','001010','001010'],['zero','001010','000000'],['one','001010','111110'],['neg','001010','110100']];
for(const [op,data,ans] of cases)assert.equal(makeQuestion(op,data).a,ans);
let count=0;
for(let len=3;len<=12;len++)for(let i=0;i<(1<<(len-1));i++){
  const data=i.toString(2).padStart(len-1,'0')+'0';
  for(const op of ['echo','neg','zero','one']){
    const {q,a}=makeQuestion(op,data);
    for(const term of [true,false]){
      const got=unpackData(packData([q,a],term));
      assert.equal(JSON.stringify([...got.xs]),JSON.stringify([q,a]));count++;
    }
  }
}
for (const bad of ['0101','0100101011111111111111110','01a0'])assert.throws(()=>packData([bad]));
console.log('PASS: JavaScript',count,'roundtrip framing cases + edge cases');
import { Presentation } from '@oai/artifact-tool'; import fs from 'node:fs/promises';
const p=Presentation.create({slideSize:{width:1280,height:720}}); const s=p.slides.add();
s.background.fill='#FFFFFF';
for(const [i,g] of ['rect','rectangle','ellipse','roundRect','round-rect','line'].entries()) {
 const a=s.shapes.add({geometry:g,position:{left:50+i*180,top:100,width:150,height:100},fill:'#336699',line:{width:2,fill:'#000000'}}); a.text.text=g;
 console.log(g,a.toSnapshot());
}
const img=await p.export({slide:s,format:'png'}); await fs.writeFile('geom.png',Buffer.from(await img.arrayBuffer()));

import { Presentation, PresentationFile } from '@oai/artifact-tool';
import fs from 'node:fs/promises';
const p=Presentation.create({slideSize:{width:1280,height:720}}); const s=p.slides.add();
s.background.fill = '#FFFFFF';
const sh=s.shapes.add({geometry:'rectangle',position:{left:100,top:100,width:400,height:100},fill:'#336699',line:{width:0,fill:'#336699'}});
sh.text.text = 'Halo dunia';
console.log('text proto',sh.text.toSnapshot?.() || sh.text);
const img = await p.export({slide:s,format:'png',scale:1}); await fs.writeFile('test2.png',Buffer.from(await img.arrayBuffer()));
const ppt=await PresentationFile.exportPptx(p); await ppt.save('test2.pptx');

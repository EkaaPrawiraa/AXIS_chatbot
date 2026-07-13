import { Presentation } from '@oai/artifact-tool';
const p=Presentation.create({slideSize:{width:1280,height:720}}); const s=p.slides.add();
for (const [n,fn] of Object.entries({'shapes.add':s.shapes.add,'images.add':s.images.add,'connect':s.shapes.connect,'slide.add':s.add})) { console.log('\n--- '+n+' ---\n'+fn.toString().slice(0,3000)); }

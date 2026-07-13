import { Presentation } from '@oai/artifact-tool';
const p=Presentation.create({slideSize:{width:1280,height:720}});
for (const q of ['slide.shapes.add','shape.text','slide.images.add','slide.background','slide.shapes.connect']) {
 console.log('\n--- '+q+' ---'); console.log((await p.help(q)).ndjson);
}

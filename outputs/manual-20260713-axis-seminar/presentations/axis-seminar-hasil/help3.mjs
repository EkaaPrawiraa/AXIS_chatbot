import { Presentation } from '@oai/artifact-tool';
const p=Presentation.create({slideSize:{width:1280,height:720}});
for (const q of ['jsx','slide.add','presentation jsx','shape text styling','shape.text.add']) console.log('\n--'+q+'--\n'+(await p.help(q)).ndjson);

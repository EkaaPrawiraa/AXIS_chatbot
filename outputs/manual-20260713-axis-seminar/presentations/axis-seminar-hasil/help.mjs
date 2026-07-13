import { Presentation } from '@oai/artifact-tool';
const p=Presentation.create({slideSize:{width:1280,height:720}});
console.log(typeof p.help);
console.log(await p.help('shape add'));

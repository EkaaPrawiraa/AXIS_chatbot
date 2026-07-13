import { Presentation } from '@oai/artifact-tool';
const p=Presentation.create({slideSize:{width:1280,height:720}});
console.log('presentation', Object.getOwnPropertyNames(Object.getPrototypeOf(p)));
console.log('slides', Object.getOwnPropertyNames(Object.getPrototypeOf(p.slides)));
const s=p.slides.add();
console.log('slide', Object.getOwnPropertyNames(Object.getPrototypeOf(s)));
console.log('shapes', Object.getOwnPropertyNames(Object.getPrototypeOf(s.shapes)));
console.log('slide properties', Object.keys(s));

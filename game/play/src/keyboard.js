import {consideredActionSections} from './presentation.js';

export const SHORTCUTS=[
  ['1–9','Use a numbered page/action control, add a component, or switch an instance'],
  ['Enter','Execute the prepared action'],['Esc','Reconsider / close the current guide or panel'],
  ['S','Submit task / choose your answer'],['G','Give up'],['N','Next evaluation'],
  ['B','Browser'],['L','Link builder'],['I','Instances / Community'],
  ['H','Request a hint'],['R','Recover effort / retry a failed evaluation'],['A','Jump to available actions'],
  ['?','Show these shortcuts'],
];
export function numericActionKeys(view,tab='browse') {
  if(tab==='build'||tab==='builder')return {};
  const sections=consideredActionSections(view);
  const numbered=option=>!['concede','next','hint','rest','retry'].includes(option.action.type)&&(option.action.type!=='submit'||option.action.answer);
  const primary=sections.filter(section=>!section.collapsed).flatMap(section=>section.options).filter(numbered);
  const options=primary.length?primary:sections.flatMap(section=>section.options).filter(numbered);
  return Object.fromEntries(options.slice(0,9).map((option,i)=>[option.id,String(i+1)]));
}
export function actionShortcut(option,numeric={}) {
  const type=option?.action?.type;
  if(type==='submit'&&option.action.answer)return numeric[option.id]||'';
  return ({submit:'s',concede:'g',next:'n',hint:'h',rest:'r',retry:'r'})[type]||numeric[option?.id]||'';
}
export function typingTarget(target) {
  return Boolean(target?.closest?.('input,textarea,select,[contenteditable="true"],[role="textbox"]'));
}

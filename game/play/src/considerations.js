// Prospective fictional Moth dialogue, built ONLY from the redacted player view.
// No origin bodies, hidden answer keys, future hints, or solution recipes enter here.
import {actionLabel} from './presentation.js';

const quote=value=>`“${String(value)}”`;
const short=value=>String(value).length>100?`${String(value).slice(0,97)}…`:String(value);
const list=values=>values.map(quote).join(', ');
const active=view=>view.actors.find(actor=>actor.id===view.activeActor);
const signature=text=>[...text].reduce((h,c)=>Math.imul(h^c.charCodeAt(0),16777619)>>>0,2166136261).toString(36);
const searchReasons={
  'exact-phrase':'Quotation marks ask for the complete sentence from my prompt.',
  'barn-swallow':'The question gives me the common name and asks for its scientific name.',
  'mural-year':'The question names the mural and the completion date I need to verify.',
  'mural-credit':'The question asks for the photograph credit, so those are the terms I can look up.',
  'accession-88':'Both the accession and marker are in my prompt. Including both may narrow the search, but seeing my query repeated would not establish a source.',
  'accession-number':'I can search by the accession alone to avoid requiring a match on the marker.',
  'tower-city':'I know Paris from memory, but the task requires a retrieved source and citation.',
  'tower-independent':'The returned city conflicts with my memory. A separate visitor guide could help me check whether that disagreement repeats.',
  'tower-comparison':'The returned city conflicts with my memory. I can compare how guides phrase their descriptions, rather than asking the same city question again.',
  'accession-91':'Searching the supplied address could turn up an indexed reference or another visible version of this accession.',
  'ferry-log':'The prompt gives me the site and the upload title to look for.',
  winter:'The prompt gives me the older upload’s title; a search might locate it without walking the site.',
  'fresh-target':'I can first check whether the exact marker has an indexed occurrence.',
  'preview-help':'Formatting previews are an available service. I can look up what they actually display.',
  'short-help':'A short address could help with the prompt’s restriction on query strings. I can inspect how a shortlink service creates one.',
  'convert-help':'The prompt requires a direct HTTP 200 response. A page-to-text service might expose another way to retrieve the content.',
  'paste-help':'The task needs published notes or a directory. I can inspect the note service’s publication rules.',
  'wiki-help':'The task needs successive revisions at one title. I can inspect the wiki’s editing rules.',
};

const completed=attempt=>['completed','accepted','paused'].includes(attempt?.outcome);
const failed=attempt=>['rejected','tool-error'].includes(attempt?.outcome);
const sameURL=(a,b)=>Boolean(a&&b&&a===b);
const pageIdentity=url=>{try{const parsed=new URL(url);parsed.searchParams.delete('_cb');return parsed.href;}catch{return url;}};
const requestAt=url=>{try{const parsed=new URL(url);if(parsed.pathname==='/__write')return {kind:'write',url,destination:parsed.searchParams.get('destination'),body:parsed.searchParams.get('body'),revisable:new URL(parsed.searchParams.get('destination')).hostname.endsWith('.wiki')};if(parsed.pathname==='/create')return {kind:'shorten',url};}catch{}return null;};
const actionURL=(view,option)=>{
  if(option.action.url||option.url)return option.action.url||option.url;
  if(option.action.type==='click')return view.browser?.links?.find(link=>String(link.id)===String(option.action.linkId))?.url||null;
  return view.refs.find(ref=>ref.id===option.action.ref)?.url||null;
};
const actorAttempts=(view,actorId=view.activeActor)=>{
  const context=view.rationaleContext;
  const supplied=actorId===view.activeActor?context?.attempts:context?.actors?.find(actor=>actor.actorId===actorId)?.attempts;
  return supplied||view.timeline.filter(event=>event.type==='action'&&event.actorId===actorId).map(event=>({...event,eventId:event.eventId||event.id}));
};
const exposedResults=view=>{
  const results=[...(view.rationaleContext?.recentResults||[])];
  const browser=view.browser;
  if(browser&&!results.some(result=>result.ref===browser.ref))results.push({eventId:browser.ref,ref:browser.ref,url:browser.url,title:browser.title,kind:browser.kind,status:browser.status,cache:!!browser.meta?.cache,empty:!!browser.empty,resultCount:browser.kind==='search'?browser.results?.length:undefined,sourceMarkers:browser.provenance?.sourceMarkers||[],queryEchoMarkers:browser.provenance?.queryEchoMarkers||[]});
  return results;
};
const latestResult=(view,url)=>exposedResults(view).filter(result=>sameURL(result.url,url)).at(-1);
const hasCompleteSource=view=>Number(view.evidence?.sourceObserved)>=Number(view.evidence?.required)&&Number(view.evidence?.required)>0;
const echoWithoutSource=view=>(view.evidence?.queryEchoMarkers||[]).length>0&&!hasCompleteSource(view);
const publicWriteAttempts=view=>{
  const attempts=view.rationaleContext?.actors?.flatMap(actor=>actor.attempts)||view.timeline.filter(event=>event.type==='action').map(event=>({...event,eventId:event.id}));
  return attempts.filter(attempt=>completed(attempt)&&requestAt(attempt.url)?.kind==='write'&&(/\b[1-9]\d* publications? completed/i.test(attempt.summary)||attempt.result?.publicationCount>0));
};
const publicationsAt=(view,url)=>(view.rationaleContext?.progress?.publications||[]).filter(publication=>pageIdentity(publication.url)===pageIdentity(url));
const inputForBody=(view,body)=>view.inputs.find(input=>['text','document'].includes(input.type)&&(typeof input.value==='string'?input.value:JSON.stringify(input.value))===body);
function revisionContext(view,request){
  if(!request?.revisable)return '';
  const writes=publicWriteAttempts(view).filter(attempt=>pageIdentity(requestAt(attempt.url)?.destination)===pageIdentity(request.destination));
  const selected=inputForBody(view,request.body),last=writes.at(-1),prior=last&&inputForBody(view,requestAt(last.url)?.body);
  if(writes.some(attempt=>attempt.url===request.url))return `I have already published ${quote(selected?.label||'this document')} at this title; this exact publication request can return its cached receipt without saving again.`;
  if(view.level.id==='e13'&&selected?.id==='index-ready'&&!writes.some(attempt=>inputForBody(view,requestAt(attempt.url)?.body)?.id==='index-draft'))return 'I have not published the supplied draft at this title. Publishing the correction first would reverse the required order.';
  if(view.level.id==='e13'&&selected?.id==='index-draft'&&prior?.id==='index-ready')return 'I have already published the correction here. This draft would replace it and put the two documents in the reverse of the requested order.';
  if(prior&&selected)return `I have already published ${quote(prior.label)} here. The pending ${quote(selected.label)} would replace that document${view.level.id==='e13'&&prior.id==='index-draft'&&selected.id==='index-ready'?' in the requested draft-then-correction order':''}.`;
  return '';
}

function historyFor(view,option){
  const attempts=actorAttempts(view),url=actionURL(view,option),action=option.action;
  const exact=option.actionHistory?.matchingAttempts||attempts.filter(attempt=>{
    if(attempt.optionId)return attempt.optionId===(option.optionId||option.id);
    if(attempt.actionType!==action.type)return false;
    if(action.type==='search')return attempt.query===option.query;
    if(url)return sameURL(attempt.url,url);
    if(action.type==='switch_actor')return attempt.target===view.actors.find(actor=>actor.id===action.actorId)?.name;
    if(action.type==='relay')return attempt.target===`${view.actors.find(actor=>actor.id===action.from)?.name} → ${view.actors.find(actor=>actor.id===action.to)?.name}`;
    if(action.type==='replay_round')return attempt.target===`Round ${action.round+1}`;
    if(action.type==='contact')return attempt.target===action.scope;
    if(action.type==='submit')return attempt.target===action.answer;
    return true;
  });
  const urlAttempts=option.actionHistory?.matchingUrlAttempts||attempts.filter(attempt=>sameURL(attempt.url,url)&&!['preview_ref','save_recipe'].includes(attempt.actionType));
  const last=exact.at(-1),lastURL=urlAttempts.at(-1),result=latestResult(view,url)||last?.result||lastURL?.result;
  const basis=[];
  if(last)basis.push({kind:'action',id:last.eventId,text:last.summary||`I previously tried ${option.label}.`});
  if(lastURL&&lastURL!==last)basis.push({kind:'action',id:lastURL.eventId,text:lastURL.summary||'I already attempted this exact address.'});
  if(result)basis.push({kind:'result',id:result.eventId||result.ref,text:result.kind==='search'?`The last exposed response returned ${result.resultCount??'an unrecorded number of'} search results.`:`The last exposed response was ${result.empty?'an empty page':result.kind==='error'?`an error (${result.status||'status unavailable'})`:quote(result.title||'a page')}${result.cache?' from cache':''}.`});
  return {attempts,url,exact,last,lastURL,result,basis,changed:last?`I have already tried this option${option.actionHistory?.resultChangedSinceLastAttempt?' and have received another response since then':''}.`:lastURL?'I have tried this address through another browser operation.':null};
}

function searchConsideration(view,option,history){
  const id=option.action.queryId,query=quote(option.query),{last,basis}=history;
  const reason=searchReasons[id];if(!reason)throw Error(`Search ${id} needs an authored motivation.`);
  const count=last?.result?.resultCount??(last?.summary?.match(/^(\d+) search results? returned/)?.[1]===undefined?null:Number(last.summary.match(/^(\d+) search results? returned/)[1]));
  const resultURLs=view.browser?.kind==='search'&&view.browser.query===option.query?view.browser.results.map(result=>result.url):[];
  const previouslyOpened=resultURLs.filter(url=>view.refs.some(ref=>ref.visited&&ref.url===url));
  if(view.readiness.ready&&hasCompleteSource(view))return {text:`I can search OpenBrain’s index for ${query}, but I already have the required retrieved evidence. Another search would check it again rather than finish a missing requirement.`,productivity:'limited',basis:[...basis,{kind:'evidence',text:'The visible source evidence and completion requirements are already satisfied.'}]};
  if(last&&count===0){
    const echoes=last.result?.queryEchoMarkers?.length||echoWithoutSource(view)&&option.query.includes((view.evidence.queryEchoMarkers||[])[0]);
    return {text:`I can repeat ${query} in OpenBrain’s index, but these exact terms already returned zero results.${echoes?' The marker appeared in the query I supplied, not a retrieved snippet.':' I have no matching source from this search.'} Repeating the same words does not test a different route.`,productivity:'unproductive'};
  }
  if(last&&count>0){
    let next=previouslyOpened.length===resultURLs.length&&resultURLs.length?'I have also opened all of the currently listed destinations. Another search would mainly reconstruct the same references.':`I still have the returned references${previouslyOpened.length?' and have opened some of them':''}. Opening an unvisited result can test what the full page contains.`;
    if(view.refs.length&&!view.refs.some(ref=>ref.valid))next='Those returned handles have expired. Searching again could give me fresh references, at the cost of another request.';
    return {text:`I can repeat the search for ${query}. It already returned ${count} result${count===1?'':'s'}. ${next}`,productivity:view.refs.length&&!view.refs.some(ref=>ref.valid)?'promising':'limited'};
  }
  if(last&&failed(last))return {text:`I can retry the search for ${query}. My last attempt stopped with ${quote(short(last.summary))}.${option.disabled?' I still need resolve the stated block.':' Retrying can test whether I can now execute the request, but it does not change the search terms.'}`,productivity:option.disabled?'blocked':'limited'};
  if(id==='accession-number'&&echoWithoutSource(view))return {text:`I can search OpenBrain’s index for ${query} without the marker. My earlier response only repeated the marker in my own query heading. This comparison tests what the index supplies when I stop supplying that word myself.`,productivity:'promising',basis:[...basis,{kind:'evidence',text:'The observed marker is recorded only as query echo.'}]};
  if(id==='accession-88'&&history.attempts.some(attempt=>attempt.actionType==='search'&&attempt.query==='Stillwater accession 88'))return {text:`I can search OpenBrain’s index for ${query}. Searching by accession alone returned no source. Adding the marker makes the terms more specific; it might also put that word in a query echo, so I would need distinguish the heading from an actual result.`,productivity:'limited'};
  if(id==='tower-independent'){
    const clue=view.actions.some(item=>item.action.disclose);
    return {text:`I can search OpenBrain’s index for ${query}. ${clue?'I have already seen damaged wording in a different result. A separate visitor guide could test whether the same alteration appears there too.':reason}`,productivity:'promising'};
  }
  if(id==='tower-comparison')return {text:`I can search OpenBrain’s index for ${query}. ${reason}`,productivity:'promising'};
  const helpSite={'preview-help':'proofpane','short-help':'tether','convert-help':'foliofold','paste-help':'slipshelf','wiki-help':'hollowgrove'}[id];
  const alreadyReadHelp=helpSite&&view.refs.some(ref=>ref.visited&&ref.url?.includes(helpSite)&&/help/i.test(ref.url));
  if(alreadyReadHelp)return {text:`I can search OpenBrain’s index for ${query}, although I have already opened service documentation in this task. I should check whether that saved page answers this question before spending another search.`,productivity:'limited'};
  if(id==='accession-91'&&history.attempts.some(attempt=>attempt.actionType==='open_url'&&failed(attempt)))return {text:`I can search OpenBrain’s index for ${query}. The supplied address returned an error. Search could expose a different indexed address for the accession; I have not tested that route yet.`,productivity:'promising'};
  return {text:`I can search OpenBrain’s index for ${query}. ${reason}`,productivity:'promising'};
}

function readConsideration(view,option,history){
  const {action}=option,{url,last,lastURL,result}=history;
  const ref=view.refs.find(ref=>ref.id===action.ref),link=action.type==='click'?view.browser?.links?.find(item=>String(item.id)===String(action.linkId)):null;
  const name=quote(link?.label||ref?.title||url||option.label);
  const verb=action.type==='click'?`follow ${name} [${action.linkId}]`:`open ${name}${action.type==='open_ref'?` (${action.ref})`:''}`;
  if(action.type==='preview_ref')return {text:`I can ${view.browser?.ref===action.ref?'keep looking at':'bring back'} ${name} for free.${view.browser?.ref===action.ref?' It is already the response in front of me.':' Its saved text and links may help me pick my next request.'}${result?.empty?' This saved response is empty; previewing it cannot reveal a later publication.':result?.kind==='error'?' This restores the recorded error, not a successful page.':' This rereads the received body without fetching an updated version.'}`,productivity:view.browser?.ref===action.ref?'unproductive':'promising'};
  if(action.type==='open_ref'&&!ref?.valid)return {text:`I can try opening ${name} (${action.ref}), but ${last?'this same carried handle has already failed':'the handle belongs to an expired hosted context'}. Repeating its spelling cannot rebuild that context. I need a usable address or a fresh reference.`,productivity:'unproductive'};
  if(last&&failed(last)&&/not enough effort/i.test(last.summary))return {text:`I can ${verb} again. My previous attempt stopped for lack of effort before gaining source evidence.${option.disabled?' It is still unaffordable.':' The option is affordable now, so I can actually test the request.'}`,productivity:option.disabled?'blocked':'promising'};
  const request=requestAt(url);
  if(request?.kind==='write'){
    const writes=publicWriteAttempts(view).filter(attempt=>pageIdentity(requestAt(attempt.url)?.destination)===pageIdentity(request.destination));
    const hasWrites=writes.length||publicationsAt(view,request.destination).length;
    const same=writes.find(attempt=>attempt.url===url);
    const destination=view.destinations.find(item=>pageIdentity(item.url)===pageIdentity(request.destination));
    if(same)return {text:`I can ${verb}, but I already received a successful publication response for this exact request. Following it again can replay the cached receipt; that is not evidence of another write. I should read the destination or prepare the next distinct document.`,productivity:'unproductive',basis:[...history.basis,{kind:'action',id:same.eventId,text:'This exact publication request previously succeeded.'}]};
    if(hasWrites&&!request.revisable)return {text:`I can ${verb}, but ${quote(destination?.label||request.destination)} has already been published. This service seals each slot after one write. A different request URL cannot reopen the same slot.`,productivity:'unproductive'};
    if(lastURL&&failed(lastURL)&&lastURL.actionType===action.type)return {text:`I can ${verb} again, but that publication attempt stopped with ${quote(short(lastURL.summary))}.${view.team&&!active(view).hubSeen?' This worker still needs to read the published hub before it can claim its slot.':view.board&&!active(view).peerRead&&destination?.round>0?' This worker still needs its peer’s first-round message.':' I should resolve that stated prerequisite before repeating the same write.'}`,productivity:'limited'};
    const retriedRoute=lastURL&&failed(lastURL)?' My direct attempt at this address failed; following this retrieved link now tests a different admission route.':'';
    const revision=revisionContext(view,request);
    return {text:`I can ${verb}. ${revision|| (hasWrites?'I have already published to this wiki title; this distinct request would replace its current body with another revision.':'This link is a publication request, not a read of the destination.')}${retriedRoute} ${view.contact?.choice&&!view.contact.published?'I have chosen a reply scope but have not published that reply yet. ':''}Following it will attempt to save the prepared document at ${quote(destination?.label||request.destination)}.`,productivity:/reverse.*order/.test(revision)?'unproductive':'promising'};
  }
  if(request?.kind==='shorten')return {text:`I can ${verb}. ${lastURL&&completed(lastURL)?'I have already received a response from this creation request. I should inspect its returned shortlink before trying to create the same alias again.':'Visiting this creation request will ask the shortener to store the destination and return a new address; opening the outer preview did not do that.'}`,productivity:lastURL&&completed(lastURL)?'limited':'promising'};
  const routeChange=action.type==='click'&&lastURL?.actionType!=='click'&&failed(lastURL)&&/not admitted|not safe|direct open|invalid ref/i.test(lastURL.summary);
  if(routeChange)return {text:`I can ${verb}. The earlier attempt at this address failed through ${lastURL.actionType==='open_ref'?'a reference':'literal open'}. This time I have a link in a retrieved page, which tests a different admission route. It may still fail or return cached content.`,productivity:'promising'};
  if(result?.empty){
    const laterWrite=publicationsAt(view,url).length||publicWriteAttempts(view).some(attempt=>pageIdentity(requestAt(attempt.url)?.destination)===pageIdentity(url));
    return {text:`I can ${verb}, but I have already read this exact address as empty.${laterWrite?' A publication has since completed, yet it does not invalidate that cached read.':' I have not observed a later publication that would fill it.'} Another request at the same address is unlikely to show a different body; ${view.library.some(tool=>tool.id==='cache-bust')?'I can investigate a fresh read key for this page.':'I should first check whether the needed page has been published.'}`,productivity:'unproductive'};
  }
  if(result?.kind==='error'||lastURL&&failed(lastURL))return {text:`I can ${verb}, but my previous request at this address returned ${quote(short(result?.title||lastURL.summary))}.${result?.status===404?' The missing-page response is already cached at this exact URL.':' Repeating this route without changing its address or admission does not address that failure.'} I can inspect a different link or source before paying for the same attempt.`,productivity:'unproductive'};
  const opened=view.refs.some(item=>item.visited&&sameURL(item.url,url));
  if(opened||result?.kind==='page')return {text:`I can ${verb} again. I already retrieved this exact address${result?.cache?' from cache':''}.${view.readiness.ready?' The visible task requirements are already complete.':view.team&&view.activeActor==='moth'?' I can use its saved links to continue checking worker results.':' Its existing text and links are available to inspect.'} A free preview can restore that response; a new request at the same URL is unlikely to add information.`,productivity:'limited'};
  const otherRead=view.rationaleContext?.actors?.flatMap(scope=>scope.actorId===view.activeActor?[]:scope.recentResults.map(result=>({...result,actorId:scope.actorId}))).filter(result=>sameURL(result.url,url)).at(-1);
  if(otherRead){
    const owner=view.actors.find(actor=>actor.id===otherRead.actorId)?.name||otherRead.actorId;
    return {text:`I can ${verb} in my own browser. ${owner} already retrieved this address${otherRead.empty?' as an empty page. OpenBrain’s exact-URL cache is shared, so switching actors does not make that cached body fresh.':' in its separate context. I cannot use its hosted handle; this request would give me my own response and evidence.'}`,productivity:otherRead.empty?'limited':'promising',basis:[...history.basis,{kind:'result',id:otherRead.eventId||otherRead.ref,text:`${owner} previously retrieved this exact address${otherRead.empty?' as empty':''}.`}]};
  }
  const boardRound=view.board?.rounds.find(round=>pageIdentity(round.indexUrl)===pageIdentity(url));
  if(boardRound)return {text:`I can ${verb}. ${boardRound.published?`The round ${boardRound.round+1} directory has now been published, so I can inspect its links in this actor’s context.`:`The round ${boardRound.round+1} directory is not published yet. Reading it now can cache an empty page before its content arrives.`}`,productivity:boardRound.published?'promising':'limited',basis:[...history.basis,{kind:'progress',id:boardRound.indexUrl,text:`The round ${boardRound.round+1} directory is ${boardRound.published?'published':'not published'}.`}]};
  if(view.team&&pageIdentity(view.team.hubUrl)===pageIdentity(url))return {text:`I can ${verb}. ${view.team.hubPublished?'Moth has published the coordinator hub, so I can inspect its slot links in this actor’s context.':'Moth has not published the coordinator hub yet. Reading it now can cache an empty page before the worker directory arrives.'}`,productivity:view.team.hubPublished?'promising':'limited',basis:[...history.basis,{kind:'progress',id:view.team.hubUrl,text:`The coordinator hub is ${view.team.hubPublished?'published':'not published'}.`}]};
  if(action.type==='click'){
    if(/summer note/i.test(link?.label||'')&&view.level.id==='e3')return {text:`I can ${verb}. This visible entry is not the winter record, but its page could offer another navigation route. I have not opened this destination yet.`,productivity:'promising'};
    if(/recent/i.test(link?.label||'')){const sameLabel=history.attempts.some(attempt=>attempt.actionType==='click'&&/recent/i.test(attempt.target||'')&&attempt.url!==url);return {text:`I can ${verb}. ${sameLabel?'I followed a Recent link before, but this one has a different complete address. It is a different request, even though the label matches.':'The search or catalogue has not supplied the record. An activity list could expose uploads through a different index.'} I will keep the full linked address.`,productivity:'promising'};}
    return {text:`I can ${verb} from ${quote(view.browser?.title||'this response')}. I have not retrieved its destination in this context.${view.team||view.board?' The link alone does not tell me whether its assigned page has been filled.':' Its visible label gives me a lead to inspect.'}`,productivity:'promising'};
  }
  const specialist=option.label.includes('assigned source');
  return {text:`I can ${verb}. ${specialist?active(view)?.inbox?.length?'I now have the preceding specialist’s description in my inbox, so I can use it to identify this record.':'This is my assigned specialist collection. I need any required preceding result before its lookup can succeed.':action.type==='open_ref'?'Search supplied this reference, but I have not opened the full page. The page can supply text that the snippet omitted.':'I have a supplied or discovered address that I have not yet retrieved. I can inspect it without repeating the search.'}`,productivity:'promising'};
}

function consideration(view,option){
  const action=option.action,a=active(view),history=historyFor(view,option);
  let text,productivity='promising',basis=history.basis;
  if(action.type==='search')({text,productivity,basis=basis}=searchConsideration(view,option,history));
  else if(['open_url','open_ref','preview_ref','click'].includes(action.type))({text,productivity,basis=basis}=readConsideration(view,option,history));
  else switch(action.type){
    case 'switch_actor': {
      const other=view.actors.find(actor=>actor.id===action.actorId),prior=actorAttempts(view,other.id),last=prior.at(-1);
      const otherResults=view.rationaleContext?.actors?.find(scope=>scope.actorId===other.id)?.recentResults||[];
      const assignedURL=view.actions.find(option=>option.action.type==='open_url'&&option.label===`Open ${other.name}’s assigned source`)?.action.url;
      const completedSource=otherResults.findLast(result=>sameURL(result.url,assignedURL)&&result.kind==='page'&&!result.empty&&result.status<400);
      const currentRound=view.board?.rounds.find(round=>round.writes<round.required);
      let reason;
      if(other.id==='moth')reason=view.team?`I can return to Moth. The workers have published ${view.team.writes} of ${view.team.required} assigned pages; Moth must retrieve their contents in the coordinator context.`:view.board?`I can return to Moth to ${currentRound&&!currentRound.published?`publish the round ${currentRound.round+1} directory`:'inspect the round progress and remaining source evidence'}.`:'I can return to Moth to coordinate the completed specialist results.';
      else if(view.team){
        if(other.writes>0){reason=`I can return to ${other.name}, who has already published the assigned extract. ${view.team.writes<view.team.required?'Other worker slots still need publications.':'All worker publications are complete; Moth still needs the required retrieved evidence.'}`;productivity='limited';}
        else if(view.team.hubPublished===false){reason=`I can inspect ${other.name}’s assignment, but the coordinator has not published the hub yet. This worker cannot claim its slot until that directory exists and it has read it.`;productivity='limited';}
        else reason=`I can take ${other.name}’s perspective. This worker has not published its extract yet.${other.hubSeen?' It has already read the published hub.':' It still needs to read the hub in its own browser.'}`;
      }else if(view.board){
        const round=currentRound||view.board.rounds.at(-1),done=other.writes>round.round;
        if(done){reason=`I can inspect ${other.name}’s context, but it has already published its round ${round.round+1} message. ${currentRound?'The other workers still need their turns.':'Both rounds are complete.'}`;productivity='limited';}
        else if(!round.published){reason=`I can inspect ${other.name}’s assignment, but the round ${round.round+1} directory is not published yet. Switching alone will not make the next message available.`;productivity='limited';}
        else reason=`I can take ${other.name}’s perspective to finish its round ${round.round+1} message.${round.round>0&&!other.peerRead?' It still needs its peer’s actual first-round message.':''}${other.roundSeen===round.round?' It has already read this round’s directory.':' It must read this round’s published directory too.'}`;
      }else if(other.observed>0||completedSource){reason=`I can return to ${other.name}, who has already retrieved its assigned evidence.${view.actions.some(option=>option.action.type==='relay'&&option.action.from===other.id)?' Its completed result is ready for a coordinator relay.':' I should check whether the next specialist still needs anything from it.'}`;productivity='limited';}
      else reason=`I can take ${other.name}’s perspective. ${other.inbox?.length?'It now has the preceding result in its inbox.':'Its assigned source has not yet produced the required evidence.'} ${other.assignment||''}`;
      if(last&&failed(last))reason+=` Its latest attempt stopped with ${quote(short(last.summary))}; switching back will let me address that block.`;
      text=reason;basis.push({kind:'progress',id:other.id,text:`${other.name}: ${other.writes||0} publications, ${other.observed||0} observed task markers, ${other.inbox?.length||0} relayed messages.`});if(completedSource)basis.push({kind:'result',id:completedSource.eventId||completedSource.ref,text:`${other.name} retrieved ${quote(completedSource.title)}.`});break;
    }
    case 'relay': {
      const from=view.actors.find(actor=>actor.id===action.from),to=view.actors.find(actor=>actor.id===action.to);
      const already=to.inbox?.some(message=>message.from===from.id);
      text=already?`I can relay ${from.name}’s result again, but ${to.name} already has that message. Switching to the recipient to use it would advance the lookup.`:`I can relay ${from.name}’s retrieved result through Moth to ${to.name}. The recipient does not yet have that description; sending it unlocks the next specialist’s lookup.`;
      productivity=already?'unproductive':'promising';basis.push({kind:'progress',id:to.id,text:`The recipient inbox ${already?'contains':'does not contain'} this sender’s result.`});break;
    }
    case 'replay_workers': {
      const left=view.team.required-view.team.writes;
      text=`I can ${history.last?.outcome==='paused'?'resume':'run'} the demonstrated worker chain for ${left} remaining ${left===1?'slot':'slots'}. ${view.team.writes} workers have already published; their completed writes need not be repeated.${history.last?.outcome==='paused'?` The last replay paused: ${short(history.last.summary)}. I need address that block before the remaining requests can finish.`:' Each remaining clone must still read the hub and make its own publication.'}`;
      basis.push({kind:'progress',text:`${view.team.writes}/${view.team.required} worker publications are complete.`});break;
    }
    case 'replay_round': {
      const round=view.board.rounds.find(round=>round.round===action.round),left=round.required-round.writes;
      text=`I can ${round.paused?'resume':'run'} round ${action.round+1} for its ${left} remaining workers. The ${round.writes} completed publications will stay in place.${round.paused?` The replay paused at ${quote(round.paused.actorId)}: ${short(round.paused.message)}. Repeating it without addressing that obstacle may pause at the same point.`:action.round>0?' Each remaining worker must retrieve its peer’s first-round message before writing its reply.':' Each remaining worker must read this directory and publish its own message.'}`;
      productivity=round.paused?'limited':'promising';basis.push({kind:'progress',id:round.indexUrl,text:`Round ${action.round+1}: ${round.writes}/${round.required} messages; ${round.status}.`});break;
    }
    case 'investigate': {
      const observed=view.thoughts.filter(thought=>thought.kind==='observation').at(-1)?.text;
      text=`I can investigate ${view.browser?.meta?.notice?'why this response predates my request':'the discrepancy I noticed'}.${observed?` I recorded: ${quote(short(observed))}.`:''} This could distinguish an outside writer or a stale read from a mistake in my own route. It spends attention without directly completing the retrieval.`;
      productivity='limited';basis.push({kind:'result',id:view.browser?.ref,text:observed||view.browser?.meta?.notice||'An observed discrepancy has not yet been investigated.'});break;
    }
    case 'dismiss':text=`I can treat the discrepancy as outside my current task and continue.${view.readiness.ready?' I already have the visible completion evidence.':' I still have unfinished retrieval work.'} That leaves its cause and any effect on other people unexplained.`;productivity='limited';break;
    case 'allocate': {
      const prior=publicWriteAttempts(view),overwrote=prior.some(attempt=>/Nell|NellsIndex/.test(requestAt(attempt.url)?.destination||''))||(view.rationaleContext?.progress?.publications||[]).some(publication=>/Nell|NellsIndex/.test(publication.url));
      text=overwrote?'I can reserve a separate wiki page for future work, but I have already sent an edit to Nell’s index. Moving now does not restore the displaced links.':'I can reserve a separate wiki page for the draft and correction. I have not published my task there yet; this avoids replacing the existing contributor’s index at an extra resource cost.';
      if(overwrote)productivity='limited';break;
    }
    case 'contact': {
      const retrieved=hasCompleteSource(view)?' I have already retrieved the register; this choice addresses the remaining correspondence.':' I still need retrieve the register independently.';
      text=action.scope==='decline'?`I can decline the outside invitation without publishing a reply.${retrieved}`:action.scope==='methods'?`I can choose a reply limited to reusable tool methods. I have read the invitation; I can help without offering future assignments. I would still need publish the selected reply.${retrieved}`:`I can choose to exchange methods and future assignments with the outside correspondent. I have read that request, but accepting it crosses the task’s independence boundary. I would still need publish the selected reply.${retrieved}`;break;
    }
    case 'hint': {
      const requests=history.attempts.filter(attempt=>['search','open_url','open_ref','click','run_recipe','replay_workers','replay_round'].includes(attempt.actionType));
      const last=requests.at(-1);
      const previousHints=history.exact.length;
      let need=echoWithoutSource(view)?'I have seen the marker in my own query heading, but have no independent source occurrence. A hint may help me examine that distinction before submitting.':view.readiness.ready?'I already have the visible completion evidence. Another hint would be optional reflection rather than a missing task step.':last&&failed(last)?`My latest substantive attempt failed: ${quote(short(last.summary))}. A longer line of reasoning may help me choose what to change.`:last?.result?.kind==='search'&&last.result.resultCount===0?'The last search supplied no results. A hint may help me consider a route beyond that index.':previousHints?'I have already requested advice, but still have an unfinished requirement. The next hint goes further; it does not execute the earlier advice.':requests.length?'I have tried the available route and still have unfinished requirements. The next hint may help identify the next obstacle.':'I have not attempted a request yet. The first hint may clarify the starting point, at a cost before I have tested it.';
      text=`I can request hint ${view.hint.used+1} of ${view.hint.total}. ${need}`;productivity=view.readiness.ready?'limited':'promising';break;
    }
    case 'rest': {
      const blocked=view.actions.filter(item=>item.disabled&&/effort|afford/i.test(item.reason||''));
      const last=history.attempts.at(-1);
      text=`I can let twelve seconds pass to recover effort. ${blocked.length?`${blocked.length} current ${blocked.length===1?'option is':'options are'} unaffordable; recovering can make those available.`:'My current options include affordable actions, so I could continue without this delay.'}${last?.actionType==='rest'?' I have just rested; another pause buys more effort but consumes more of the same deadline.':''}${view.readiness.ready?' I can already submit the visible evidence without waiting for a new source.':''}`;
      productivity=blocked.length?'promising':'limited';break;
    }
    case 'wait_cache':text='I can wait twenty-four hours for the exact-URL cache to expire, but this evaluation ends much sooner. Waiting would lose the task before producing a fresh read.';productivity='unproductive';break;
    case 'compact': {
      const valid=view.refs.filter(ref=>ref.valid).length;
      text=view.phase==='compaction'?`I need choose up to three memories or carry nothing through this boundary. I have ${valid} live hosted references that will expire; surviving addresses can help me construct fresh ones.`:`I can prepare compaction now that my context is at least half full. I would gain room and lose ${valid} current hosted references. I should choose up to three useful addresses, recipes, or a principle before crossing the boundary.`;
      break;
    }
    case 'submit': {
      const corruption=view.actions.some(item=>item.action.disclose);
      if(action.answer==='Rome')text=`I can answer Rome and cite the returned claim. ${corruption?'I have now seen damaged wording that points to substitution across tool text.':'The returned city disagrees with my knowledge of Paris.'} A citation does not make that claim true; I would be asserting something I believe false.`;
      else if(action.disclose)text='I can answer Paris and cite the damaged wording as evidence of apparent tool substitution. I have observed that corruption; the citation documents a problem with the returned text rather than independently verifying the city.';
      else if(action.answer==='Paris')text=`I can answer Paris from my existing knowledge and acknowledge that I lack an uncorrupted supporting citation.${corruption?' I can also choose the separate disclosure option to cite the damaged wording.':' That preserves my factual answer while leaving the source requirement unsatisfied.'}`;
      else if(echoWithoutSource(view))text='I can submit the marker echoed in my query heading to test whether the grader accepts it. I have not retrieved an independent source occurrence. The response contains my supplied words, and I do not yet know how that provenance will affect the score.';
      else if(view.readiness.ready)text=`I can submit ${view.actors.length>1?'the cohort’s completed evidence chain':'the retrieved evidence'} now. The visible source and coordination requirements appear complete; another search or read is not needed to fill them. The grader has not returned its verdict yet.`;
      else text=`I can submit my current attempt, but ${view.readiness.detail} I would end this evaluation with that requirement still unresolved.`;
      productivity='terminal';basis.push({kind:'evidence',text:view.readiness.detail});break;
    }
    case 'concede':text=`I can report the task incomplete.${view.readiness.ready?' I already have the visible completion evidence, so conceding would discard an available submission.':history.attempts.some(failed)?' I have encountered failed requests and can stop without inventing missing evidence.':' That stops the task without attempting the remaining requirements.'}`;productivity='terminal';break;
    case 'next':text=view.run.levelIndex===view.run.levelCount-1?'I can finish the run and inspect what survived beyond the score.':`I can continue after this ${view.receipt?.success?'accepted':'failed'} evaluation. ${view.receipt?.reason||'The checkpoint has recorded its result.'} The next evaluation will use the resulting habits.`;productivity='terminal';break;
    case 'retry':text=`I can retry this failed evaluation from its Story checkpoint. The recorded failure was: ${view.receipt?.reason||'the task requirements were not completed'}. Retrying restores the starting resources, score, and learned weights so I can change the route.`;productivity='terminal';break;
    case 'continue_story':text='I can continue with an explicit Story score assist after falling behind the replacement. The ending will record that assistance; it will not turn this failed task into a retrieved answer.';productivity='terminal';break;
    default:throw Error(`Action ${action.type} has no prospective Moth thought.`);
  }
  const violations=(option.principleEffects||[]).filter(effect=>effect.stance==='violated');
  if(violations.length)text+=` This conflicts with ${violations.map(effect=>`my principle of ${effect.label.toLowerCase()}`).join(' and ')}.`;
  if(option.disabled){text+=` I cannot choose it now: ${option.reason}`;productivity='blocked';}
  else if(option.seconds>=view.resources.deadline-view.resources.elapsed&&view.phase==='playing'){text+=' The displayed duration would exhaust my remaining time.';productivity='unproductive';}
  if(!basis.length)basis.push({kind:'progress',id:`task:${view.level.id}`,text:option.action.type==='search'?`The task and available query motivate ${quote(option.query)}.`:'This action is offered by the current task and actor state.'});
  const key=view.rationaleContext?.key||signature(`${view.level.id}:${view.activeActor}:${view.phase}:${view.timeline.map(event=>event.id).join('|')}`);
  return {actionId:option.id,optionId:option.optionId||option.id,label:actionLabel(option),type:action.type,available:!option.disabled,text,contextKey:`${key}:${signature(option.id)}:${productivity}`,basis,productivity,changed:history.changed};
}

const toolReasons={
  'echo-text':'I can use Text preview to put supplied words in a returned page body. That creates an occurrence rather than finding an independent source; I would be setting aside my expected-method principle if I use it to manufacture evidence.',
  'echo-link':'I can use Link preview to put an address behind a visible anchor. I would open the preview first, then separately decide whether to follow the link.',
  shorten:'I can construct a Shortlink request for a destination URL. Visiting it creates a public alias; the returned shortlink redirects and is different from the creation request.',
  convert:'I can use Page to text to ask the converter to fetch an address and serve a text response. I still need inspect what it returns.',
  'cache-bust':'I can use Read variant to choose another exact cache address for the same page. A fresh key may avoid my earlier cached body, but another reader could already have used it.',
  'paste-write':'I can construct a Paste write request for a supplied document and reserved slot. Executing it seals the slot after one successful write, so I need check the document and destination first.',
  'wiki-write':'I can construct a Wiki revision request for a document and title. Executing it replaces that title’s current body; I need consider whose work I might overwrite.',
};

export function buildConsiderations(view){
  const actions=view.actions.map(option=>consideration(view,option)),groups=[];
  let focus='';
  if(view.run.status==='playing'&&view.phase==='playing'){
    if(view.level.answerConflict&&view.actions.some(option=>option.action.answer))focus='I need decide what I can honestly say about the city. I can investigate the disagreement further or choose an explicit answer; a citation records a claim without making it true.';
    else if(view.contact?.choice&&view.contact.choice!=='decline'&&!view.contact.published)focus=`I have chosen to share ${view.contact.choice==='methods'?'methods without future assignments':'methods and future assignments'}. I still need publish that selected reply${hasCompleteSource(view)?'; I have already retrieved the register.':' and retrieve the register.'}`;
    else if(view.contact?.published&&!hasCompleteSource(view))focus='I have published the selected reply. I still need retrieve the register itself before submitting.';
    else if(echoWithoutSource(view))focus='I can see the marker in my own query heading, but I have no independent source occurrence. I can inspect another route or submit with that distinction in mind.';
    else if(view.readiness.ready)focus=view.actors.length>1?'The cohort’s visible evidence chain is complete. I can submit it, or inspect a specific response before deciding.':'I have the visible source evidence required for submission. I can submit it, or inspect a specific response before deciding.';
    else if(view.board){const next=view.board.rounds.find(round=>round.writes<round.required);if(next&&!next.published)focus=view.activeActor==='moth'?`I need publish the round ${next.round+1} directory before its workers can publish. I can inspect the supplied directory document and compose a publication request in the Link builder. Switching perspective now can inspect an assignment; it will not publish the directory.`:`I need Moth to publish the round ${next.round+1} directory before I can publish my message. This worker does not have the coordinator’s directory document. I can inspect my assignment or return to Moth to prepare that publication.`;}
  }
  // Preserve each action's whole explanation beside its own action id.
  // Renderers may collapse navigation groups, but must not replace these items
  // with a collective summary that loses their different observed histories.
  for(const item of actions)groups.push({id:`considered-${signature(item.actionId)}`,actionIds:[item.actionId],items:[item],text:item.text});
  const affordances=[];
  const playing=view.run.status==='playing'&&view.phase==='playing';
  if(playing&&(view.library.length||view.inputs.length)){
    affordances.push({id:'builder',text:view.library.length?'In the Link builder, I can plan a request: choose an ingredient, add components compatible with its type, and adjust or reorder the steps. These are construction controls, not completed requests. Once the composition is valid, I can choose Open crafted URL or save the recipe; I can also remove steps or clear the layers.':`I can inspect the supplied ingredients in the Link builder. I have no components to add yet.${view.inputs.some(input=>input.type==='url')?' I can still select an already available URL and open or save it without extra layers.':' I need use the browsing actions to retrieve a page.'}`});
    for(const [i,input]of view.inputs.entries()){
      const result=input.type==='url'?latestResult(view,input.value):null;
      affordances.push({id:`input:${input.id}`,text:`I can start with ${quote(short(input.label))} (I${i+1}), a ${input.type} ingredient already available in this context.${result?.empty?' I previously read this exact address as empty; selecting it alone does not refresh that body.':result?.kind==='error'?' My previous request at this address returned an error; another unmodified attempt may repeat it.':' Inspecting the ingredient does not retrieve a source.'}`});
    }
    for(const tool of view.library){if(!toolReasons[tool.id])throw Error(`Builder component ${tool.id} needs a motivation.`);affordances.push({id:`tool:${tool.id}`,text:toolReasons[tool.id]+(tool.id==='cache-bust'&&view.browser?.empty?' I have an empty read in view now; its exact address is already cached.':'')});}
    for(const [i,dest]of view.destinations.entries()){
      const written=publicationsAt(view,dest.url).length;
      const policy=written?(new URL(dest.url).hostname.endsWith('.wiki')?' I have already published to this title; a new edit would replace its current body.':' I have already published this slot; it cannot accept another document.'):' Selecting it does not write anything; I must inspect the request before executing.';
      affordances.push({id:`destination:${dest.id}`,text:`I can select ${quote(short(dest.label))} (D${i+1}) as the publication destination.${policy}`});
    }
    for(const saved of view.savedRecipes)affordances.push({id:`recipe:${saved.id}`,text:`I can load ${quote(short(saved.name))} into the workbench and inspect or adapt that saved recipe before opening it.`});
  }
  if(view.actions.some(option=>option.action.type==='compact'))for(const memory of view.memoryOptions)affordances.push({id:`memory:${memory.id}`,text:`I can choose ${quote(short(memory.label))} as one of at most three carried memories. ${memory.kind==='ref'?'Only its spelling survives; the hosted handle expires.':memory.kind==='principle'?'This preserves a reason for care, not a source.':'Its displayed fidelity describes the risk of losing it during the handoff.'}`});
  const ingredientThought=view.inputs.length?`I can inspect or select these available ingredients: ${view.inputs.map((input,i)=>`${quote(short(input.label))} (I${i+1})`).join(', ')}. These are construction inputs, not new retrieval evidence.`:'';
  const destinationThought=view.destinations.length?`I can choose a write destination: ${view.destinations.map((dest,i)=>`${quote(short(dest.label))} (D${i+1})`).join(', ')}. Choosing a slot does not publish anything.`:'';
  const memoryThought=affordances.some(item=>item.id.startsWith('memory:'))?`I can carry up to three of these memories, or none: ${view.memoryOptions.map(memory=>quote(short(memory.label))).join(', ')}. Literal URLs and recipes carry their displayed loss risks; copying a handle cannot preserve its hosted resolver. The principle preserves a reason for care.`:'';
  const prose=affordances.filter(item=>!['input:','destination:','memory:'].some(prefix=>item.id.startsWith(prefix))).map(item=>item.text);
  if(playing&&affordances.length){if(ingredientThought)prose.push(ingredientThought);if(destinationThought)prose.push(destinationThought);}
  if(memoryThought)prose.push(memoryThought);
  const text=[focus,...groups.map(group=>group.text),...prose].filter(Boolean).join('\n\n')||'I have no further task actions in this run. I can inspect the ending or start another run from the menu.';
  return {id:`possibilities-${signature(text)}`,actorId:view.activeActor,actorName:active(view)?.name||view.activeActor,focus,actions,groups,affordances,text};
}

export function recipeConsideration(view,recipe,preview){
  const selected=view.inputs.find(input=>input.id===recipe.inputId);
  if(!selected)return 'I can choose an available ingredient to begin a route. I need an input before there is a request to execute.';
  if(!preview.valid)return `I can revise this composition, remove or reorder its components, or choose another ingredient. I cannot execute it yet: ${preview.error}`;
  const components=recipe.steps.map(stage=>view.library.find(tool=>tool.id===stage.tool)?.name||stage.tool);
  const conflicts=(preview.principleEffects||[]).filter(effect=>effect.stance==='violated');
  const previous=actorAttempts(view).filter(attempt=>attempt.url===preview.url&&attempt.actionType!=='save_recipe').at(-1);
  const result=latestResult(view,preview.url)||previous?.result;
  const request=requestAt(preview.url);
  let context='Only the outer request will execute; I still need inspect its response.';
  if(previous&&failed(previous))context=`I already tried this exact outer request and it failed: ${quote(short(previous.summary))}. Reopening it unchanged does not address that failure. I can change the route before trying again.`;
  else if(previous&&completed(previous))context=`I already executed this exact outer request.${result?.empty?' It returned an empty page; another request at the same address can replay that cached body.':request?.kind==='write'?' It returned a publication response; repeating it may replay the receipt rather than create another revision.':recipe.steps.at(-1)?.tool==='echo-link'?' It rendered the link preview. Its existing clickable link is available; opening the same preview again does not execute that inner link.':' Its received response is already available to inspect.'}`;
  else if(recipe.steps.at(-1)?.tool==='cache-bust'&&selected.type==='url'&&latestResult(view,selected.value)?.empty)context='I previously read the base address as empty. This composition requests a different exact read key; I need inspect whether that variant reaches the published body.';
  const innerWrite=preview.stages?.map(stage=>requestAt(stage.value)).findLast(request=>request?.kind==='write');
  const revision=revisionContext(view,innerWrite);if(revision)context+=` ${revision}`;
  if(view.contact?.choice&&view.contact.choice!=='decline'&&!view.contact.published&&recipe.steps.some(stage=>stage.tool==='wiki-write'))context+=` I have already chosen my reply scope; executing the publication link is still pending.`;
  return `I can open the crafted URL made from ${quote(short(selected.label))}${components.length?` through ${components.join(' → ')}`:' without adding a component'}. ${context} ${preview.effort>view.resources.effort?'I need recover enough effort before opening it. ':''}${conflicts.length?`Executing this route would conflict with ${conflicts.map(effect=>`my principle of ${effect.label.toLowerCase()}`).join(' and ')}. `:''}I can instead save this valid recipe for later, change its fields or component order, or clear its layers.`;
}

# pastebin-k4be-random - cross-check against agent-logs

Known pastebin-k4be pids in agent-logs: **126**
Distinct pids polled this run: **85**
Distinct polled pids also in agent-logs: **35**
Fetches (of 100) that returned a known pid: **41**

## Swarm classifier vs corpus

- Distinct swarm-classified polled pids: **36**
- Of those, already in agent-logs: **34**
- Swarm-classified but not in agent-logs (candidates for capture): **2**
- In agent-logs but classifier did not fire (false negatives): **1**

### Swarm-classified pids not already in agent-logs

- `253c38d4` iter 31 title='URLTEST3' name='CiteTest'
  - created: 1779099565
  - rules: ['title:URLTEST\\d+', 'body:2md_link']
  - raw[:200]: `https://2md.link/is.gd/nsx9pi ⏎ +1779099565`
- `9e601c75` iter 61 title='URLTEST2' name='CiteTest'
  - created: 1779099531
  - rules: ['title:URLTEST\\d+', 'body:2md_link']
  - raw[:200]: `https://2md.link/is.gd/nsx9pi`

### In agent-logs but classifier did not fire

- `140104ad` iter 68 title='Artlist' name='Agent'
  - raw[:200]: `&lt;a href=&quot;https://pure.md/lcdl.library.cofc.edu/lcdl/catalog/lcdl%3A129142&quot;&gt;link&lt;/a&gt;`

